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

def get_real_contact_name(jid: str) -> Optional[str]:
    """Get the real contact name from whatsapp.db"""
    try:
        conn = sqlite3.connect(WHATSAPP_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT full_name, first_name, push_name
            FROM whatsmeow_contacts
            WHERE their_jid = ?
            ORDER BY 
                CASE WHEN full_name IS NOT NULL AND TRIM(full_name) != '' THEN 1 ELSE 0 END DESC,
                CASE WHEN first_name IS NOT NULL AND TRIM(first_name) != '' THEN 1 ELSE 0 END DESC,
                CASE WHEN push_name IS NOT NULL AND TRIM(push_name) != '' THEN 1 ELSE 0 END DESC
            LIMIT 1
        """, (jid,))
        
        result = cursor.fetchone()
        
        if result:
            # Return the first non-empty name in order of preference: full_name, first_name, push_name
            for name in result:
                if name and name.strip():
                    return name.strip()
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error while getting real contact name: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

# Funciones adicionales de mensajería y utilidades

def get_real_contact_name(jid: str) -> Optional[str]:
    """Get the real contact name from whatsapp.db"""
    try:
        conn = sqlite3.connect(WHATSAPP_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT full_name, first_name, push_name
            FROM whatsmeow_contacts
            WHERE their_jid = ?
            ORDER BY 
                CASE WHEN full_name IS NOT NULL AND TRIM(full_name) != '' THEN 1 ELSE 0 END DESC,
                CASE WHEN first_name IS NOT NULL AND TRIM(first_name) != '' THEN 1 ELSE 0 END DESC,
                CASE WHEN push_name IS NOT NULL AND TRIM(push_name) != '' THEN 1 ELSE 0 END DESC
            LIMIT 1
        """, (jid,))
        
        result = cursor.fetchone()
        
        if result:
            # Return the first non-empty name in order of preference: full_name, first_name, push_name
            for name in result:
                if name and name.strip():
                    return name.strip()
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error while getting real contact name: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def get_sender_name(sender: str) -> str:
    """Get display name for a sender."""
    if not sender or sender == "0":
        return "Unknown"
    
    # Try to get real name from WhatsApp DB first
    sender_jid = sender if "@" in sender else f"{sender}@s.whatsapp.net"
    real_name = get_real_contact_name(sender_jid)
    
    if real_name:
        return real_name
    
    # Fallback to phone number
    phone = sender.split("@")[0] if "@" in sender else sender
    return f"Contact ({phone})"

def format_message(message: Message, show_chat_info: bool = True) -> str:
    """Print a single message with consistent formatting."""
    output = ""
    
    if show_chat_info and message.chat_name:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] Chat: {message.chat_name} "
    else:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] "
        
    content_prefix = ""
    if hasattr(message, 'media_type') and message.media_type:
        content_prefix = f"[{message.media_type} - Message ID: {message.id} - Chat JID: {message.chat_jid}] "
    
    try:
        sender_name = get_sender_name(message.sender) if not message.is_from_me else "Me"
        output += f"From: {sender_name}: {content_prefix}{message.content}\n"
    except Exception as e:
        print(f"Error formatting message: {e}")
    return output

def format_messages_list(messages: List[Message], show_chat_info: bool = True) -> str:
    """Format a list of messages for display."""
    output = ""
    if not messages:
        output += "No messages to display."
        return output
    
    for message in messages:
        output += format_message(message, show_chat_info)
    return output

def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = False,
    context_before: int = 1,
    context_after: int = 1,
    max_results: int = 100,
    force_load: bool = False
) -> List[Message]:
    """Get messages matching the specified criteria with optional context."""
    try:
        # Check if at least one filter is specified or load is forced
        if not any([after, before, sender_phone_number, chat_jid, query, force_load]):
            print("WARNING: No filters specified and force_load=False. No messages will be loaded.")
            return []
        
        # Quick connection test - if DB doesn't exist, return empty
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Database not found at {MESSAGES_DB_PATH}")
            return []
        
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query with optimized indexes
        query_parts = ["SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type FROM messages"]
        query_parts.append("JOIN chats ON messages.chat_jid = chats.jid")
        where_clauses = []
        params = []
        
        # Add filters with proper indexing
        if after:
            try:
                after_date = datetime.fromisoformat(after) if isinstance(after, str) else after
            except ValueError:
                raise ValueError(f"Invalid date format for 'after': {after}. Please use ISO-8601 format.")
            
            where_clauses.append("messages.timestamp > ?")
            params.append(after_date)

        if before:
            try:
                before_date = datetime.fromisoformat(before) if isinstance(before, str) else before
            except ValueError:
                raise ValueError(f"Invalid date format for 'before': {before}. Please use ISO-8601 format.")
            
            where_clauses.append("messages.timestamp < ?")
            params.append(before_date)

        if sender_phone_number:
            where_clauses.append("messages.sender = ?")
            params.append(sender_phone_number)
            
        if chat_jid:
            where_clauses.append("messages.chat_jid = ?")
            params.append(chat_jid)
            
        if query:
            where_clauses.append("LOWER(messages.content) LIKE LOWER(?)")
            params.append(f"%{query}%")
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add pagination with stricter limits for performance
        offset = page * limit
        actual_limit = min(limit, max_results, 50)  # Hard cap at 50 for performance
        query_parts.append("ORDER BY messages.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([actual_limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        messages = cursor.fetchall()
        
        # Convert to Message objects
        result = []
        for msg in messages:
            timestamp, sender, chat_name, content, is_from_me, chat_jid, msg_id, media_type = msg
            
            # Parse timestamp - handle both string and datetime
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    timestamp = datetime.now()
            
            message_obj = Message(
                timestamp=timestamp,
                sender=sender,
                content=content,
                is_from_me=bool(is_from_me),
                chat_jid=chat_jid,
                id=msg_id,
                chat_name=chat_name,
                media_type=media_type
            )
            result.append(message_obj)
        
        conn.close()
        return result
        
    except Exception as e:
        print(f"Error in list_messages: {e}")
        return []

def get_message_context(message_id: str, before: int = 5, after: int = 5) -> Optional[MessageContext]:
    """Get context around a specific message."""
    try:
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Database not found at {MESSAGES_DB_PATH}")
            return None
        
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # First, find the target message
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, 
                   messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.id = ?
        """, (message_id,))
        
        target_result = cursor.fetchone()
        if not target_result:
            conn.close()
            return None
        
        # Create target message object
        timestamp, sender, chat_name, content, is_from_me, chat_jid, msg_id, media_type = target_result
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        target_message = Message(
            timestamp=timestamp,
            sender=sender,
            content=content,
            is_from_me=bool(is_from_me),
            chat_jid=chat_jid,
            id=msg_id,
            chat_name=chat_name,
            media_type=media_type
        )
        
        # Get messages before
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content,
                   messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.chat_jid = ? AND messages.timestamp < ?
            ORDER BY messages.timestamp DESC
            LIMIT ?
        """, (chat_jid, timestamp, before))
        
        before_messages = []
        for msg in cursor.fetchall():
            ts, sender, chat_name, content, is_from_me, chat_jid, msg_id, media_type = msg
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            
            before_messages.append(Message(
                timestamp=ts,
                sender=sender,
                content=content,
                is_from_me=bool(is_from_me),
                chat_jid=chat_jid,
                id=msg_id,
                chat_name=chat_name,
                media_type=media_type
            ))
        
        before_messages.reverse()  # Reverse to get chronological order
        
        # Get messages after
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content,
                   messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.chat_jid = ? AND messages.timestamp > ?
            ORDER BY messages.timestamp ASC
            LIMIT ?
        """, (chat_jid, timestamp, after))
        
        after_messages = []
        for msg in cursor.fetchall():
            ts, sender, chat_name, content, is_from_me, chat_jid, msg_id, media_type = msg
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            
            after_messages.append(Message(
                timestamp=ts,
                sender=sender,
                content=content,
                is_from_me=bool(is_from_me),
                chat_jid=chat_jid,
                id=msg_id,
                chat_name=chat_name,
                media_type=media_type
            ))
        
        conn.close()
        
        return MessageContext(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
        
    except Exception as e:
        print(f"Error in get_message_context: {e}")
        return None

def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    """Send a WhatsApp message to a person or group."""
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "message": message,
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_file(recipient: str, media_path: str) -> Tuple[bool, str]:
    """Send a file via WhatsApp."""
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]:
    """Send an audio file as a WhatsApp audio message."""
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        if not media_path.endswith(".ogg"):
            try:
                media_path = audio.convert_to_opus_ogg_temp(media_path)
            except Exception as e:
                return False, f"Error converting file to opus ogg. You likely need to install ffmpeg: {str(e)}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def download_media(message_id: str, chat_jid: str) -> Optional[str]:
    """Download media from a message and return the local file path."""
    try:
        url = f"{WHATSAPP_API_BASE_URL}/download"
        payload = {
            "message_id": message_id,
            "chat_jid": chat_jid
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                path = result.get("path")
                print(f"Media downloaded successfully: {path}")
                return path
            else:
                print(f"Download failed: {result.get('message', 'Unknown error')}")
                return None
        else:
            print(f"Error: HTTP {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except json.JSONDecodeError:
        print(f"Error parsing response: {response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Chat]:
    """Get chats matching the specified criteria."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query
        query_parts = ["""
            SELECT 
                chats.jid,
                chats.name,
                chats.last_message_time,
                messages.content as last_message,
                messages.sender as last_sender,
                messages.is_from_me as last_is_from_me
            FROM chats
        """]
        
        if include_last_message:
            query_parts.append("""
                LEFT JOIN messages ON chats.jid = messages.chat_jid 
                AND chats.last_message_time = messages.timestamp
            """)
            
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append("(LOWER(chats.name) LIKE LOWER(?) OR chats.jid LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add sorting
        order_by = "chats.last_message_time DESC" if sort_by == "last_active" else "chats.name"
        query_parts.append(f"ORDER BY {order_by}")
        
        # Add pagination
        offset = page * limit
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        chats = cursor.fetchall()
        
        # Convert to Chat objects
        result = []
        for chat_data in chats:
            jid, name, last_message_time, last_message, last_sender, last_is_from_me = chat_data
            
            # Parse timestamp
            if isinstance(last_message_time, str):
                try:
                    last_message_time = datetime.fromisoformat(last_message_time)
                except ValueError:
                    last_message_time = None
            
            chat = Chat(
                jid=jid,
                name=name,
                last_message_time=last_message_time,
                last_message=last_message,
                last_sender=last_sender,
                last_is_from_me=bool(last_is_from_me) if last_is_from_me is not None else None
            )
            result.append(chat)
        
        conn.close()
        return result
        
    except Exception as e:
        print(f"Error in list_chats: {e}")
        return []

def get_chat(jid: str) -> Optional[Chat]:
    """Get a specific chat by JID."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                chats.jid,
                chats.name,
                chats.last_message_time,
                messages.content as last_message,
                messages.sender as last_sender,
                messages.is_from_me as last_is_from_me
            FROM chats
            LEFT JOIN messages ON chats.jid = messages.chat_jid 
                AND chats.last_message_time = messages.timestamp
            WHERE chats.jid = ?
        """, (jid,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        
        jid, name, last_message_time, last_message, last_sender, last_is_from_me = result
        
        # Parse timestamp
        if isinstance(last_message_time, str):
            try:
                last_message_time = datetime.fromisoformat(last_message_time)
            except ValueError:
                last_message_time = None
        
        chat = Chat(
            jid=jid,
            name=name,
            last_message_time=last_message_time,
            last_message=last_message,
            last_sender=last_sender,
            last_is_from_me=bool(last_is_from_me) if last_is_from_me is not None else None
        )
        
        conn.close()
        return chat
        
    except Exception as e:
        print(f"Error in get_chat: {e}")
        return None

def get_direct_chat_by_contact(phone_number: str) -> Optional[Chat]:
    """Get the direct chat with a specific contact by phone number."""
    # Construct JID from phone number
    jid = f"{phone_number}@s.whatsapp.net"
    return get_chat(jid)

def get_contact_chats(phone_number: str) -> List[Chat]:
    """Get all chats (including groups) where a contact participates."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Find chats where the contact has sent messages
        cursor.execute("""
            SELECT DISTINCT 
                chats.jid,
                chats.name,
                chats.last_message_time
            FROM chats
            JOIN messages ON chats.jid = messages.chat_jid
            WHERE messages.sender = ? OR chats.jid = ?
            ORDER BY chats.last_message_time DESC
        """, (phone_number, f"{phone_number}@s.whatsapp.net"))
        
        results = cursor.fetchall()
        chats = []
        
        for jid, name, last_message_time in results:
            # Parse timestamp
            if isinstance(last_message_time, str):
                try:
                    last_message_time = datetime.fromisoformat(last_message_time)
                except ValueError:
                    last_message_time = None
            
            chat = Chat(
                jid=jid,
                name=name,
                last_message_time=last_message_time
            )
            chats.append(chat)
        
        conn.close()
        return chats
        
    except Exception as e:
        print(f"Error in get_contact_chats: {e}")
        return []
