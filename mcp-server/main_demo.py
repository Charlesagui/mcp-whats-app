#!/usr/bin/env python3
"""
WhatsApp MCP Server - Servidor MCP seguro para WhatsApp (Versión Demo)
"""

import requests
import json
import sys
import os
from typing import Dict, Any, Optional

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv("../.env")

class WhatsAppMCPDemo:
    def __init__(self):
        self.bridge_url = f"http://{os.getenv('MCP_HOST', '127.0.0.1')}:{os.getenv('BRIDGE_PORT', '8081')}"
        self.admin_token = os.getenv('ADMIN_TOKEN', 'default_admin_token')
        
    def _get_headers(self) -> Dict[str, str]:
        """Obtener headers de autenticación para el bridge"""
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Hacer solicitud HTTP al bridge de WhatsApp"""
        url = f"{self.bridge_url}/api/v1{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data or {})
            else:
                response = requests.post(url, headers=headers, json=data or {})
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            raise Exception(f"Error comunicándose con WhatsApp bridge: {str(e)}")
    
    def search_contacts(self, query: str = "") -> str:
        """Buscar contactos por nombre o número de teléfono."""
        try:
            result = self._make_request("GET", "/contacts", {"search": query})
            if result.get("success"):
                contacts = result.get("data", [])
                if contacts:
                    contact_list = []
                    for contact in contacts:
                        contact_list.append(f"• {contact['name']} ({contact['jid']})")
                    return f"Contactos encontrados:\n" + "\n".join(contact_list)
                else:
                    return f"No se encontraron contactos que coincidan con '{query}'"
            else:
                return f"Error buscando contactos: {result.get('error', 'Error desconocido')}"
        except Exception as e:
            return f"Error buscando contactos: {str(e)}"
    
    def list_messages(self, chat_jid: str = "", limit: int = 50) -> str:
        """Listar mensajes de WhatsApp."""
        try:
            params = {"limit": limit}
            if chat_jid:
                params["chat_jid"] = chat_jid
            
            result = self._make_request("GET", "/messages", params)
            if result.get("success"):
                messages = result.get("data", [])
                if messages:
                    message_list = []
                    for msg in messages:
                        timestamp = msg['timestamp']
                        sender = msg['sender_jid']
                        content = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                        message_list.append(f"[{timestamp}] {sender}: {content}")
                    return f"Mensajes ({len(messages)}):\n" + "\n".join(message_list)
                else:
                    return "No se encontraron mensajes"
            else:
                return f"Error obteniendo mensajes: {result.get('error', 'Error desconocido')}"
        except Exception as e:
            return f"Error obteniendo mensajes: {str(e)}"
    
    def send_message(self, chat_jid: str, content: str) -> str:
        """Enviar un mensaje de WhatsApp."""
        try:
            data = {
                "chat_jid": chat_jid,
                "content": content
            }
            
            result = self._make_request("POST", "/messages", data)
            if result.get("success"):
                msg_data = result.get("data", {})
                mode = msg_data.get("mode", "unknown")
                return f"Mensaje enviado correctamente ({mode}). ID: {msg_data.get('message_id', 'N/A')}"
            else:
                return f"Error enviando mensaje: {result.get('error', 'Error desconocido')}"
        except Exception as e:
            return f"Error enviando mensaje: {str(e)}"
    
    def get_health(self) -> str:
        """Verificar el estado de salud del bridge de WhatsApp."""
        try:
            result = self._make_request("GET", "/health")
            if result.get("success"):
                health_data = result.get("data", {})
                status = health_data.get("status", "unknown")
                connected = health_data.get("connected", False)
                timestamp = health_data.get("timestamp", "N/A")
                mode = health_data.get("mode", "unknown")
                msg_count = health_data.get("messages_count", 0)
                
                return f"""Estado del bridge: {status}
Conectado a WhatsApp: {connected}
Modo: {mode}
Mensajes: {msg_count}
Última verificación: {timestamp}"""
            else:
                return f"Error verificando salud: {result.get('error', 'Error desconocido')}"
        except Exception as e:
            return f"Error verificando salud del bridge: {str(e)}"

def main():
    """Función principal - modo interactivo para pruebas"""
    print("WhatsApp MCP Demo - Servidor de prueba")
    print("=" * 50)
    
    mcp = WhatsAppMCPDemo()
    
    # Verificar conexión
    print("Verificando conexion con el bridge...")
    health_result = mcp.get_health()
    print(health_result)
    print()
    
    # Menú interactivo
    while True:
        print("\nOpciones disponibles:")
        print("1. Verificar estado de salud")
        print("2. Listar mensajes")
        print("3. Buscar contactos")
        print("4. Enviar mensaje (demo)")
        print("5. Salir")
        
        choice = input("\nSelecciona una opcion (1-5): ").strip()
        
        if choice == "1":
            print("\nEstado de salud:")
            print(mcp.get_health())
            
        elif choice == "2":
            chat_jid = input("Chat JID (opcional, presiona Enter para todos): ").strip()
            limit = input("Limite de mensajes (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            
            print(f"\nMensajes:")
            print(mcp.list_messages(chat_jid, limit))
            
        elif choice == "3":
            query = input("Buscar contacto (nombre o numero): ").strip()
            print(f"\nContactos:")
            print(mcp.search_contacts(query))
            
        elif choice == "4":
            chat_jid = input("Chat JID de destino: ").strip()
            content = input("Mensaje a enviar: ").strip()
            
            if chat_jid and content:
                print(f"\nEnviando mensaje:")
                print(mcp.send_message(chat_jid, content))
            else:
                print("Chat JID y contenido son requeridos")
                
        elif choice == "5":
            print("\nHasta luego!")
            break
            
        else:
            print("Opcion invalida")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServidor detenido por el usuario")
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)
