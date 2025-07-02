import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Tuple
import os
import os.path
import requests
import json
import audio
import unicodedata
from dotenv import load_dotenv
from unidecode import unidecode
from fuzzywuzzy import process, fuzz

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def normalize(text):
    """Normaliza el texto eliminando acentos y convirtiéndolo a minúsculas."""
    if not text:
        return ""
    return unidecode(text).lower()

# Configuration from environment
WHATSAPP_API_HOST = os.getenv('WHATSAPP_API_HOST', 'localhost')
WHATSAPP_API_PORT = os.getenv('WHATSAPP_API_PORT', '8080')
WHATSAPP_API_BASE_URL = os.getenv('WHATSAPP_API_BASE_URL', f'http://{WHATSAPP_API_HOST}:{WHATSAPP_API_PORT}/api')
MESSAGES_DB_NAME = os.getenv('MESSAGES_DB_NAME', 'messages.db')

# Database paths
MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', MESSAGES_DB_NAME)
WHATSAPP_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'whatsapp.db')

@dataclass
class Message:
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_jid: str
    id: str
    chat_name: Optional[str] = None
    media_type: Optional[str] = None

@dataclass
class Chat:
    jid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None

    @property
    def is_group(self) -> bool:
        """Determine if chat is a group based on JID pattern."""
        return self.jid.endswith("@g.us")

@dataclass
class Contact:
    phone_number: str
    name: Optional[str]
    jid: str

@dataclass
class MessageContext:
    message: Message
    before: List[Message]
    after: List[Message]

def get_all_contacts_with_names() -> List[Tuple[str, str, str]]:
    """Obtiene todos los contactos con sus nombres desde ambas BDs.
    Returns: Lista de tuplas (jid, display_name, source)
    """
    contacts = []
    contact_jids = set() # Usar un set para manejar duplicados eficientemente

    try:
        # 1. Obtener nombres reales de WhatsApp DB (nombres personalizados)
        if os.path.exists(WHATSAPP_DB_PATH):
            whatsapp_conn = sqlite3.connect(WHATSAPP_DB_PATH)
            whatsapp_cursor = whatsapp_conn.cursor()
            
            # Consulta corregida para buscar nombres de manera más robusta
            whatsapp_cursor.execute("""
                SELECT 
                    their_jid,
                    COALESCE(
                        NULLIF(TRIM(full_name), ''),
                        NULLIF(TRIM(first_name), ''),
                        NULLIF(TRIM(push_name), '')
                    ) as display_name
                FROM whatsmeow_contacts
                WHERE their_jid IS NOT NULL AND (
                    (full_name IS NOT NULL AND TRIM(full_name) != '') OR
                    (first_name IS NOT NULL AND TRIM(first_name) != '') OR
                    (push_name IS NOT NULL AND TRIM(push_name) != '')
                )
            """)
            
            whatsapp_contacts = whatsapp_cursor.fetchall()
            for jid, display_name in whatsapp_contacts:
                if jid not in contact_jids:
                    contacts.append((jid, display_name, 'whatsapp'))
                    contact_jids.add(jid)
            
            whatsapp_conn.close()
            
    except Exception as e:
        print(f"Error accessing WhatsApp contacts DB: {e}")
    
    try:
        # 2. Obtener chats de Messages DB (nombres de chat/grupo)
        if os.path.exists(MESSAGES_DB_PATH):
            messages_conn = sqlite3.connect(MESSAGES_DB_PATH)
            messages_cursor = messages_conn.cursor()
            
            messages_cursor.execute("""
                SELECT DISTINCT 
                    jid,
                    name
                FROM chats
                WHERE jid != '0@s.whatsapp.net'
                AND name IS NOT NULL 
                AND TRIM(name) != ''
            """)
            
            chat_contacts = messages_cursor.fetchall()
            
            for jid, name in chat_contacts:
                if jid not in contact_jids: # Evitar duplicados de la fuente anterior
                    contacts.append((jid, name, 'chat'))
                    contact_jids.add(jid)
            
            messages_conn.close()
            
    except Exception as e:
        print(f"Error accessing Messages DB: {e}")
    
    return contacts

def search_contacts(query: str, limit: int = 25, include_groups: bool = False) -> List[Contact]:
    """Búsqueda optimizada de contactos usando nombres reales de WhatsApp."""
    try:
        if not query or len(query.strip()) < 1:
            print("INFO: Query too short, returning empty results")
            return []
        
        clean_query = query.strip()
        normalized_query = normalize(clean_query)
        
        # Obtener todos los contactos con nombres
        all_contacts = get_all_contacts_with_names()
        
        if not all_contacts:
            print("WARNING: No contacts found in databases")
            return []
        
        # Filtrar grupos si no se incluyen
        if not include_groups:
            all_contacts = [(jid, name, source) for jid, name, source in all_contacts 
                          if not jid.endswith('@g.us')]
        
        # Crear lista para búsqueda fuzzy
        contact_dict = {}
        search_targets = []
        
        for jid, name, source in all_contacts:
            # Priorizar nombres de WhatsApp sobre nombres de chat
            if jid in contact_dict and source == 'chat' and contact_dict[jid]['source'] == 'whatsapp':
                continue
                
            contact_dict[jid] = {'name': name, 'source': source}
            search_targets.append((jid, normalize(name), name))
        
        # Búsqueda exacta primero
        exact_matches = []
        fuzzy_candidates = []
        
        for jid, normalized_name, original_name in search_targets:
            if normalized_query == normalized_name:
                exact_matches.append((jid, original_name, 100))
            elif normalized_query in normalized_name:
                # Calcular score basado en posición y longitud
                pos = normalized_name.find(normalized_query)
                length_ratio = len(normalized_query) / len(normalized_name)
                if pos == 0:  # Empieza con la query
                    score = 95 - (len(normalized_name) - len(normalized_query)) * 2
                else:  # Contiene la query
                    score = 85 - pos * 2 - (len(normalized_name) - len(normalized_query))
                score = max(score, 60)  # Mínimo 60
                exact_matches.append((jid, original_name, score))
            else:
                fuzzy_candidates.append((jid, normalized_name, original_name))
        
        # Búsqueda fuzzy para candidatos restantes
        fuzzy_matches = []
        if fuzzy_candidates and len(normalized_query) >= 2:
            # Extraer solo los nombres normalizados para fuzzywuzzy
            candidate_names = [name for _, name, _ in fuzzy_candidates]
            
            # Usar fuzz.partial_ratio para mejor detección de coincidencias parciales
            fuzzy_results = process.extract(
                normalized_query, 
                candidate_names, 
                scorer=fuzz.partial_ratio,
                limit=limit * 2
            )
            
            # Mapear resultados de vuelta a contactos
            for fuzzy_name, score in fuzzy_results:
                if score >= 70:  # Umbral de similitud
                    # Encontrar el contacto original
                    for jid, norm_name, orig_name in fuzzy_candidates:
                        if norm_name == fuzzy_name:
                            fuzzy_matches.append((jid, orig_name, score))
                            break
        
        # Combinar y ordenar resultados
        all_matches = exact_matches + fuzzy_matches
        all_matches.sort(key=lambda x: x[2], reverse=True)  # Ordenar por score
        
        # Eliminar duplicados manteniendo el mejor score
        seen_jids = set()
        unique_matches = []
        for jid, name, score in all_matches:
            if jid not in seen_jids:
                seen_jids.add(jid)
                unique_matches.append((jid, name, score))
        
        # Convertir a objetos Contact
        result = []
        for jid, name, score in unique_matches[:limit]:
            phone_number = jid.split('@')[0] if '@' in jid else jid
            
            contact = Contact(
                phone_number=phone_number,
                name=name,
                jid=jid
            )
            result.append(contact)
        
        return result
        
    except Exception as e:
        print(f"Error in search_contacts: {e}")
        return []

def search_contacts_enhanced(query: str, limit: int = 25, include_groups: bool = False) -> List[Contact]:
    """Alias para compatibilidad - usa la función principal mejorada."""
    return search_contacts(query, limit, include_groups)

def smart_search_contacts(query: str, limit: int = 25, include_groups: bool = False, similarity_threshold: float = 0.6) -> List[Contact]:
    """Búsqueda inteligente con umbral de similitud personalizable."""
    try:
        if not query or len(query.strip()) < 1:
            return []
        
        clean_query = query.strip()
        normalized_query = normalize(clean_query)
        
        # Obtener todos los contactos
        all_contacts = get_all_contacts_with_names()
        
        if not all_contacts:
            return []
        
        # Filtrar grupos si no se incluyen
        if not include_groups:
            all_contacts = [(jid, name, source) for jid, name, source in all_contacts 
                          if not jid.endswith('@g.us')]
        
        # Preparar para búsqueda fuzzy
        contact_dict = {}
        search_targets = []
        
        for jid, name, source in all_contacts:
            if jid in contact_dict and source == 'chat' and contact_dict[jid]['source'] == 'whatsapp':
                continue
                
            contact_dict[jid] = {'name': name, 'source': source}
            search_targets.append((jid, normalize(name), name))
        
        # Búsqueda fuzzy con umbral personalizable
        candidate_names = [(jid, norm_name, orig_name) for jid, norm_name, orig_name in search_targets]
        names_only = [norm_name for _, norm_name, _ in candidate_names]
        
        # Usar token_sort_ratio para mejor manejo de nombres con orden diferente
        fuzzy_results = process.extract(
            normalized_query,
            names_only,
            scorer=fuzz.token_sort_ratio,
            limit=limit * 2
        )
        
        # Convertir umbral de 0.0-1.0 a 0-100
        threshold_score = similarity_threshold * 100
        
        # Filtrar por umbral y mapear a contactos
        result = []
        seen_jids = set()
        
        for fuzzy_name, score in fuzzy_results:
            if score >= threshold_score:
                # Encontrar contacto original
                for jid, norm_name, orig_name in candidate_names:
                    if norm_name == fuzzy_name and jid not in seen_jids:
                        seen_jids.add(jid)
                        phone_number = jid.split('@')[0] if '@' in jid else jid
                        
                        contact = Contact(
                            phone_number=phone_number,
                            name=orig_name,
                            jid=jid
                        )
                        result.append(contact)
                        break
        
        return result[:limit]
        
    except Exception as e:
        print(f"Error in smart_search_contacts: {e}")
        return []

def smart_search_contacts_enhanced(query: str, limit: int = 25, include_groups: bool = False, similarity_threshold: float = 0.6) -> List[Contact]:
    """Alias para compatibilidad."""
    return smart_search_contacts(query, limit, include_groups, similarity_threshold)

