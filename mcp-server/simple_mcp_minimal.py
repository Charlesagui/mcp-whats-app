#!/usr/bin/env python3
"""
WhatsApp MCP Server - Versión con urllib (sin dependencias externas)
"""

import json
import sys
import os
import urllib.request
import urllib.parse
import urllib.error

class WhatsAppMCP:
    def __init__(self):
        host = os.getenv('MCP_HOST', '127.0.0.1')
        port = os.getenv('BRIDGE_PORT', '8081')
        self.bridge_url = f"http://{host}:{port}"
        
        self.admin_token = os.getenv('ADMIN_TOKEN')
        if not self.admin_token:
            raise ValueError("ADMIN_TOKEN no está configurado en las variables de entorno")
        
    def _make_request(self, method, endpoint, data=None):
        """Hacer peticiones HTTP usando urllib (incluido en Python)"""
        try:
            url = f"{self.bridge_url}/api/v1{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            if method.upper() == "GET" and data:
                # Para GET, agregar parámetros a la URL
                query_string = urllib.parse.urlencode(data)
                url = f"{url}?{query_string}"
                req_data = None
            elif method.upper() == "POST" and data:
                # Para POST, enviar como JSON
                req_data = json.dumps(data).encode('utf-8')
            else:
                req_data = None
            
            # Crear la petición
            request = urllib.request.Request(url, data=req_data, headers=headers)
            
            # Realizar la petición con timeout
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
                
        except urllib.error.URLError as e:
            if hasattr(e, 'reason'):
                raise Exception(f"Error: No se puede conectar al bridge de WhatsApp en {self.bridge_url}. ¿Está ejecutándose whatsapp-bridge.exe? ({e.reason})")
            else:
                raise Exception(f"Error de URL: {e}")
        except urllib.error.HTTPError as e:
            raise Exception(f"Error HTTP del bridge de WhatsApp: {e.code} - {e.reason}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error: Respuesta inválida del bridge de WhatsApp")
        except Exception as e:
            raise Exception(f"Error conectando a WhatsApp: {str(e)}")

def handle_mcp_request(request):
    mcp = WhatsAppMCP()
    request_id = request.get("id", 0)
    
    if request.get("method") == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "whatsapp-secure", "version": "1.0.0"}
            }
        }
    
    elif request.get("method") == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "get_health",
                        "description": "Verificar estado de WhatsApp REAL",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {},
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "list_messages",
                        "description": "Listar mensajes REALES de WhatsApp",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "description": "Número de mensajes (máximo 50)", "minimum": 1, "maximum": 50}
                            },
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "send_message",
                        "description": "Enviar mensaje REAL por WhatsApp",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "chat_jid": {"type": "string", "description": "Número de teléfono con formato: 549XXXXXXXXX@s.whatsapp.net"},
                                "content": {"type": "string", "description": "Contenido del mensaje a enviar"}
                            },
                            "required": ["chat_jid", "content"],
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "list_contacts",
                        "description": "Listar contactos de WhatsApp",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "search": {"type": "string", "description": "Buscar contacto por nombre (opcional)"}
                            },
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "send_message_by_name",
                        "description": "Enviar mensaje REAL por WhatsApp buscando por nombre de contacto",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "contact_name": {"type": "string", "description": "Nombre del contacto a buscar"},
                                "content": {"type": "string", "description": "Contenido del mensaje a enviar"}
                            },
                            "required": ["contact_name", "content"],
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "send_message_smart",
                        "description": "Enviar mensaje REAL por WhatsApp (busca automáticamente por nombre o usa número directo)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "recipient": {"type": "string", "description": "Nombre del contacto (ej: 'veci hermosa') o número con formato 549XXXXXXXXX@s.whatsapp.net"},
                                "content": {"type": "string", "description": "Contenido del mensaje a enviar"}
                            },
                            "required": ["recipient", "content"],
                            "additionalProperties": False
                        }
                    }
                ]
            }
        }
    
    elif request.get("method") == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        try:
            if tool_name == "get_health":
                result = mcp._make_request("GET", "/health")
                health = result.get("data", {})
                
                status = health.get('status', 'unknown')
                connected = health.get('connected', False)
                messages_count = health.get('messages_count', 0)
                mode = health.get('mode', 'unknown')
                
                text = f"🔍 Estado WhatsApp REAL:\n"
                text += f"• Estado: {status}\n"
                text += f"• Conectado: {'✅ Sí' if connected else '❌ No'}\n"
                text += f"• Mensajes disponibles: {messages_count}\n"
                text += f"• Modo: {mode}\n"
                
                if not connected:
                    text += f"\n⚠️ WhatsApp no está conectado. Necesitas reconectar desde tu dispositivo."
            
            elif tool_name == "list_messages":
                limit = tool_args.get("limit", 5)
                # Limitar el número máximo de mensajes
                limit = min(max(limit, 1), 50)
                
                result = mcp._make_request("GET", "/messages", {"limit": limit})
                messages = result.get("data", [])
                
                if messages:
                    text = f"📱 Últimos {len(messages)} mensajes REALES de WhatsApp:\n\n"
                    for i, msg in enumerate(messages, 1):
                        timestamp = msg.get('timestamp', 'Sin fecha')
                        sender = msg.get('sender_jid', 'Desconocido')
                        content = msg.get('content', 'Sin contenido')
                        
                        # Truncar contenido muy largo
                        if len(content) > 100:
                            content = content[:97] + "..."
                        
                        text += f"{i}. [{timestamp}]\n"
                        text += f"   De: {sender}\n"
                        text += f"   📝 {content}\n\n"
                else:
                    text = "📱 No hay mensajes disponibles en WhatsApp"
            
            elif tool_name == "send_message":
                chat_jid = tool_args.get("chat_jid", "").strip()
                content = tool_args.get("content", "").strip()
                
                # Validaciones
                if not chat_jid:
                    text = "❌ Error: Se requiere el campo 'chat_jid'"
                elif not content:
                    text = "❌ Error: Se requiere el campo 'content'"
                elif "@s.whatsapp.net" not in chat_jid:
                    text = "❌ Error: El chat_jid debe tener formato: 549XXXXXXXXX@s.whatsapp.net"
                else:
                    # Enviar mensaje usando POST
                    send_data = {
                        "chat_jid": chat_jid,
                        "content": content
                    }
                    
                    result = mcp._make_request("POST", "/messages", send_data)
                    
                    if result.get("success"):
                        data = result.get("data", {})
                        message_id = data.get("message_id", "")
                        timestamp = data.get("timestamp", "")
                        mode = data.get("mode", "")
                        
                        text = f"✅ Mensaje enviado exitosamente por WhatsApp REAL!\n\n"
                        text += f"📤 Para: {chat_jid}\n"
                        text += f"💬 Contenido: {content}\n"
                        text += f"🆔 ID del mensaje: {message_id}\n"
                        text += f"⏰ Timestamp: {timestamp}\n"
                        text += f"🔗 Modo: {mode}"
                    else:
                        error = result.get("error", "Error desconocido")
                        text = f"❌ Error enviando mensaje: {error}"
            
            elif tool_name == "list_contacts":
                search_query = tool_args.get("search", "").strip()
                
                # Buscar contactos
                search_data = {"search": search_query} if search_query else {}
                result = mcp._make_request("GET", "/contacts", search_data)
                
                if result.get("success"):
                    contacts = result.get("data", [])
                    
                    if contacts:
                        if search_query:
                            text = f"🔍 Contactos encontrados para '{search_query}':\n\n"
                        else:
                            text = f"📞 Lista de contactos de WhatsApp:\n\n"
                        
                        for i, contact in enumerate(contacts, 1):
                            name = contact.get('name', 'Sin nombre')
                            jid = contact.get('jid', 'Sin JID')
                            text += f"{i}. 👤 {name}\n"
                            text += f"   📱 {jid}\n\n"
                    else:
                        if search_query:
                            text = f"🔍 No se encontraron contactos para '{search_query}'"
                        else:
                            text = "📞 No hay contactos disponibles aún.\n\n⏳ Los contactos se sincronizan automáticamente cuando WhatsApp está conectado."
                else:
                    error = result.get("error", "Error desconocido")
                    text = f"❌ Error obteniendo contactos: {error}"
            
            elif tool_name == "send_message_by_name":
                contact_name = tool_args.get("contact_name", "").strip()
                content = tool_args.get("content", "").strip()
                
                if not contact_name:
                    text = "❌ Error: Se requiere el campo 'contact_name'"
                elif not content:
                    text = "❌ Error: Se requiere el campo 'content'"
                else:
                    # Buscar el contacto por nombre
                    search_data = {"search": contact_name}
                    contacts_result = mcp._make_request("GET", "/contacts", search_data)
                    
                    if contacts_result.get("success"):
                        contacts = contacts_result.get("data", [])
                        
                        if not contacts:
                            text = f"❌ No se encontró ningún contacto con el nombre '{contact_name}'"
                        elif len(contacts) == 1:
                            # Contacto único encontrado, enviar mensaje
                            contact = contacts[0]
                            chat_jid = contact.get('jid', '')
                            contact_display_name = contact.get('name', 'Sin nombre')
                            
                            send_data = {
                                "chat_jid": chat_jid,
                                "content": content
                            }
                            
                            send_result = mcp._make_request("POST", "/messages", send_data)
                            
                            if send_result.get("success"):
                                data = send_result.get("data", {})
                                message_id = data.get("message_id", "")
                                timestamp = data.get("timestamp", "")
                                
                                text = f"✅ Mensaje enviado exitosamente a '{contact_display_name}'!\n\n"
                                text += f"👤 Para: {contact_display_name} ({chat_jid})\n"
                                text += f"💬 Contenido: {content}\n"
                                text += f"🆔 ID del mensaje: {message_id}\n"
                                text += f"⏰ Timestamp: {timestamp}"
                            else:
                                error = send_result.get("error", "Error desconocido")
                                text = f"❌ Error enviando mensaje a '{contact_display_name}': {error}"
                        else:
                            # Múltiples contactos encontrados
                            text = f"🔍 Se encontraron {len(contacts)} contactos con '{contact_name}':\n\n"
                            for i, contact in enumerate(contacts, 1):
                                name = contact.get('name', 'Sin nombre')
                                jid = contact.get('jid', 'Sin JID')
                                text += f"{i}. 👤 {name} ({jid})\n"
                            text += f"\n💡 Especifica mejor el nombre para enviar el mensaje."
                    else:
                        error = contacts_result.get("error", "Error desconocido")
                        text = f"❌ Error buscando contacto: {error}"
            
            elif tool_name == "send_message_smart":
                recipient = tool_args.get("recipient", "").strip()
                content = tool_args.get("content", "").strip()
                
                if not recipient:
                    text = "❌ Error: Se requiere el campo 'recipient'"
                elif not content:
                    text = "❌ Error: Se requiere el campo 'content'"
                else:
                    # Detectar si es un número de teléfono o un nombre
                    if "@s.whatsapp.net" in recipient:
                        # Es un número directo, enviar inmediatamente
                        send_data = {
                            "chat_jid": recipient,
                            "content": content
                        }
                        
                        result = mcp._make_request("POST", "/messages", send_data)
                        
                        if result.get("success"):
                            data = result.get("data", {})
                            message_id = data.get("message_id", "")
                            timestamp = data.get("timestamp", "")
                            
                            text = f"✅ Mensaje enviado exitosamente!\n\n"
                            text += f"📤 Para: {recipient}\n"
                            text += f"💬 Contenido: {content}\n"
                            text += f"🆔 ID del mensaje: {message_id}\n"
                            text += f"⏰ Timestamp: {timestamp}"
                        else:
                            error = result.get("error", "Error desconocido")
                            text = f"❌ Error enviando mensaje: {error}"
                    else:
                        # Es un nombre, buscar en contactos
                        search_data = {"search": recipient}
                        contacts_result = mcp._make_request("GET", "/contacts", search_data)
                        
                        if contacts_result.get("success"):
                            contacts = contacts_result.get("data", [])
                            
                            if not contacts:
                                text = f"❌ No se encontró ningún contacto con el nombre '{recipient}'\n\n"
                                text += f"💡 Tip: También puedes usar el número directo en formato 549XXXXXXXXX@s.whatsapp.net"
                            elif len(contacts) == 1:
                                # Contacto único encontrado, enviar mensaje
                                contact = contacts[0]
                                chat_jid = contact.get('jid', '')
                                contact_display_name = contact.get('name', 'Sin nombre')
                                
                                send_data = {
                                    "chat_jid": chat_jid,
                                    "content": content
                                }
                                
                                send_result = mcp._make_request("POST", "/messages", send_data)
                                
                                if send_result.get("success"):
                                    data = send_result.get("data", {})
                                    message_id = data.get("message_id", "")
                                    timestamp = data.get("timestamp", "")
                                    
                                    text = f"✅ Mensaje enviado exitosamente a '{contact_display_name}'!\n\n"
                                    text += f"👤 Para: {contact_display_name} ({chat_jid})\n"
                                    text += f"💬 Contenido: {content}\n"
                                    text += f"🆔 ID del mensaje: {message_id}\n"
                                    text += f"⏰ Timestamp: {timestamp}"
                                else:
                                    error = send_result.get("error", "Error desconocido")
                                    text = f"❌ Error enviando mensaje a '{contact_display_name}': {error}"
                            else:
                                # Múltiples contactos encontrados
                                text = f"🔍 Se encontraron {len(contacts)} contactos con '{recipient}':\n\n"
                                for i, contact in enumerate(contacts, 1):
                                    name = contact.get('name', 'Sin nombre')
                                    jid = contact.get('jid', 'Sin JID')
                                    text += f"{i}. 👤 {name} ({jid})\n"
                                text += f"\n💡 Especifica mejor el nombre para enviar el mensaje."
                        else:
                            error = contacts_result.get("error", "Error desconocido")
                            text = f"❌ Error buscando contacto: {error}"
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": f"Herramienta desconocida: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": text}]
                }
            }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -1, 
                    "message": f"Error WhatsApp: {str(e)}"
                }
            }
    
    # Manejo de métodos no reconocidos
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601, 
            "message": "Method not found"
        }
    }

def main():
    print("🚀 WhatsApp MCP Server REAL iniciado (urllib)", file=sys.stderr)
    
    # Verificar conexión con el bridge al inicio
    try:
        mcp = WhatsAppMCP()
        result = mcp._make_request("GET", "/health")
        health_data = result.get('data', {})
        connected = health_data.get('connected', False)
        messages = health_data.get('messages_count', 0)
        
        print(f"✅ Bridge conectado correctamente", file=sys.stderr)
        print(f"📱 WhatsApp conectado: {'Sí' if connected else 'No'}", file=sys.stderr)
        print(f"📨 Mensajes disponibles: {messages}", file=sys.stderr)
        
        if not connected:
            print("⚠️  ADVERTENCIA: WhatsApp no está conectado", file=sys.stderr)
            
    except Exception as e:
        print(f"❌ ERROR: No se pudo conectar con el bridge: {e}", file=sys.stderr)
        print("❌ El MCP no funcionará sin el bridge de WhatsApp", file=sys.stderr)
    
    # Loop principal para mantener el servidor vivo
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:  # EOF
                    print("📴 EOF recibido, cerrando servidor", file=sys.stderr)
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                print(f"🔄 Procesando: {line[:50]}...", file=sys.stderr)
                request = json.loads(line)
                response = handle_mcp_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
                print(f"✅ Respondido método: {request.get('method')}", file=sys.stderr)
                
            except json.JSONDecodeError as e:
                print(f"❌ Error JSON: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"❌ Error procesando: {e}", file=sys.stderr)
                continue
                
    except EOFError:
        print("📴 Cliente desconectado", file=sys.stderr)
    except KeyboardInterrupt:
        print("🛑 Servidor detenido por usuario", file=sys.stderr)
    except Exception as e:
        print(f"💥 Error fatal: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
