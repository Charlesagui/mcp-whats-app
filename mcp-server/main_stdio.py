#!/usr/bin/env python3
"""
WhatsApp MCP Server - Versión simplificada para Claude Desktop
Usa stdio para comunicarse con Claude Desktop directamente
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("../.env")

class WhatsAppMCPStdio:
    def __init__(self):
        self.bridge_url = f"http://{os.getenv('MCP_HOST', '127.0.0.1')}:{os.getenv('BRIDGE_PORT', '8081')}"
        self.admin_token = os.getenv('ADMIN_TOKEN', 'default_admin_token')
        
    def _get_headers(self) -> Dict[str, str]:
        """Obtener headers de autenticación para el bridge"""
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
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
                return f"Mensaje enviado correctamente. ID: {msg_data.get('message_id', 'N/A')}"
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
                
                return f"Estado del bridge: {status}\nConectado a WhatsApp: {connected}\nÚltima verificación: {timestamp}"
            else:
                return f"Error verificando salud: {result.get('error', 'Error desconocido')}"
        except Exception as e:
            return f"Error verificando salud del bridge: {str(e)}"

    def handle_request(self, request: Dict) -> Dict:
        """Manejar solicitudes MCP"""
        method = request.get("method", "")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "whatsapp-mcp-secure",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "search_contacts",
                            "description": "Buscar contactos por nombre o número de teléfono",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Texto a buscar en nombres o números de contactos"
                                    }
                                }
                            }
                        },
                        {
                            "name": "list_messages",
                            "description": "Listar mensajes de WhatsApp",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "chat_jid": {
                                        "type": "string",
                                        "description": "ID del chat (opcional)"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Número máximo de mensajes (default: 50)"
                                    }
                                }
                            }
                        },
                        {
                            "name": "send_message",
                            "description": "Enviar un mensaje de WhatsApp",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "chat_jid": {
                                        "type": "string",
                                        "description": "ID del chat de destino"
                                    },
                                    "content": {
                                        "type": "string", 
                                        "description": "Contenido del mensaje"
                                    }
                                },
                                "required": ["chat_jid", "content"]
                            }
                        },
                        {
                            "name": "get_health",
                            "description": "Verificar el estado de salud del bridge de WhatsApp",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            
            try:
                if tool_name == "search_contacts":
                    result = self.search_contacts(tool_args.get("query", ""))
                elif tool_name == "list_messages":
                    result = self.list_messages(
                        tool_args.get("chat_jid", ""),
                        tool_args.get("limit", 50)
                    )
                elif tool_name == "send_message":
                    result = self.send_message(
                        tool_args.get("chat_jid", ""),
                        tool_args.get("content", "")
                    )
                elif tool_name == "get_health":
                    result = self.get_health()
                else:
                    result = f"Herramienta desconocida: {tool_name}"
                
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result
                            }
                        ]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -1,
                        "message": str(e)
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": "Method not found"
                }
            }

def main():
    """Función principal para comunicación stdio con Claude Desktop"""
    server = WhatsAppMCPStdio()
    
    # Verificar conexión con el bridge
    try:
        server._make_request("GET", "/health")
        print("WhatsApp MCP Server iniciado correctamente", file=sys.stderr)
    except Exception as e:
        print(f"Error conectando con WhatsApp bridge: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Loop principal para procesar requests
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
