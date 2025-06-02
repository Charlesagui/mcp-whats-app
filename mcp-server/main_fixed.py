#!/usr/bin/env python3
"""WhatsApp MCP Server - Versión completa y funcional"""
import json, sys, os, urllib.request, urllib.parse, urllib.error, time
from typing import Optional, Dict, Any, List

def load_env_file():
    """Carga variables de entorno desde archivo .env"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')

# Cargar variables de entorno al inicio
load_env_file()

# Configuración y esquemas de herramientas
TOOLS_SCHEMA = {
    "get_health": {
        "name": "get_health", 
        "description": "Verificar estado de conexión de WhatsApp", 
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}
    },
    "list_messages": {
        "name": "list_messages", 
        "description": "Listar mensajes recientes de WhatsApp", 
        "inputSchema": {
            "type": "object", 
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Número máximo de mensajes a mostrar"}
            }, 
            "additionalProperties": False
        }
    },
    "list_contacts": {
        "name": "list_contacts", 
        "description": "Listar contactos de WhatsApp", 
        "inputSchema": {
            "type": "object", 
            "properties": {
                "search": {"type": "string", "description": "Término de búsqueda para filtrar contactos"}
            }, 
            "additionalProperties": False
        }
    },
    "send_message_smart": {
        "name": "send_message_smart", 
        "description": "Enviar mensaje de WhatsApp por nombre de contacto o número", 
        "inputSchema": {
            "type": "object", 
            "properties": {
                "recipient": {"type": "string", "description": "Nombre del contacto o número de teléfono"}, 
                "content": {"type": "string", "description": "Contenido del mensaje a enviar"}
            }, 
            "required": ["recipient", "content"], 
            "additionalProperties": False
        }
    },
    "get_chats": {
        "name": "get_chats",
        "description": "Obtener lista de chats activos",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}
    }
}

class WhatsAppMCP:
    def __init__(self):
        self.host = os.getenv('MCP_HOST', '127.0.0.1')
        self.port = os.getenv('BRIDGE_PORT', '8081')
        self.bridge_url = f"http://{self.host}:{self.port}"
        
        self.admin_token = os.getenv('ADMIN_TOKEN')
        if not self.admin_token:
            print("ADVERTENCIA: ADMIN_TOKEN no está configurado", file=sys.stderr)
            self.admin_token = "c80502a4c4594f6730bc320274a289847ac29e02a627e866a8066d768a081c77"  # Token por defecto
        
        self.headers = {
            "Authorization": f"Bearer {self.admin_token}", 
            "Content-Type": "application/json"
        }
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 10) -> Dict[str, Any]:
        """Realizar petición HTTP al bridge de WhatsApp"""
        url = f"{self.bridge_url}/api/v1{endpoint}"
        
        if method == "GET" and data:
            query_params = urllib.parse.urlencode(data)
            url += f"?{query_params}"
            data = None
        elif data:
            data = json.dumps(data).encode('utf-8')
        
        try:
            request = urllib.request.Request(url, data=data, headers=self.headers)
            request.get_method = lambda: method
            
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
                
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            try:
                error_response = json.loads(e.read().decode('utf-8'))
                if 'error' in error_response:
                    error_msg = error_response['error']
            except:
                pass
            raise Exception(error_msg)
        except urllib.error.URLError as e:
            raise Exception(f"Error de conexión: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error decodificando respuesta JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"Error inesperado: {str(e)}")

    def _create_response(self, request_id: int, content: str) -> Dict[str, Any]:
        """Crear respuesta MCP estándar"""
        return {
            "jsonrpc": "2.0", 
            "id": request_id, 
            "result": {
                "content": [{"type": "text", "text": content}]
            }
        }

    def _create_error_response(self, request_id: int, error_msg: str, code: int = -1) -> Dict[str, Any]:
        """Crear respuesta de error MCP"""
        return {
            "jsonrpc": "2.0", 
            "id": request_id, 
            "error": {
                "code": code, 
                "message": error_msg
            }
        }

    def get_health(self) -> str:
        """Obtener estado de salud del bridge"""
        try:
            result = self._make_request("GET", "/health")
            health_data = result.get("data", {})
            
            status = health_data.get('status', 'unknown')
            connected = health_data.get('connected', False)
            messages_count = health_data.get('messages_count', 0)
            mode = health_data.get('mode', 'unknown')
            
            status_text = "✅ Conectado" if connected else "❌ Desconectado"
            
            return f"""Estado de WhatsApp:
• Estado: {status}
• Conexión: {status_text}
• Modo: {mode}
• Mensajes en memoria: {messages_count}
• Bridge URL: {self.bridge_url}"""
            
        except Exception as e:
            return f"❌ Error obteniendo estado: {str(e)}"

    def list_messages(self, limit: int = 5) -> str:
        """Listar mensajes recientes"""
        try:
            limit = max(1, min(limit, 50))  # Entre 1 y 50
            result = self._make_request("GET", "/messages", {"limit": limit})
            messages = result.get("data", [])
            
            if not messages:
                return "📭 No hay mensajes disponibles"
            
            text = f"📱 Últimos {len(messages)} mensajes:\n\n"
            for i, msg in enumerate(messages, 1):
                sender = msg.get('sender_jid', 'unknown')
                if sender == 'self':
                    sender = '📤 Tú'
                else:
                    # Simplificar JID para mostrar
                    sender = sender.replace('@s.whatsapp.net', '').replace('@g.us', ' (grupo)')
                
                content = msg.get('content', '')
                if len(content) > 100:
                    content = content[:100] + "..."
                
                timestamp = msg.get('timestamp', '')
                msg_type = msg.get('message_type', 'text')
                
                text += f"{i}. {sender}\n"
                text += f"   💬 {content}\n"
                if msg_type != 'text':
                    text += f"   📎 Tipo: {msg_type}\n"
                text += f"   🕐 {timestamp}\n\n"
            
            return text
            
        except Exception as e:
            return f"❌ Error listando mensajes: {str(e)}"

    def list_contacts(self, search: str = "") -> str:
        """Listar contactos"""
        try:
            params = {"search": search} if search else {}
            result = self._make_request("GET", "/contacts", params)
            contacts = result.get("data", [])
            
            if not contacts:
                search_msg = f" con '{search}'" if search else ""
                return f"📞 No hay contactos disponibles{search_msg}"
            
            search_msg = f" (búsqueda: '{search}')" if search else ""
            text = f"📞 Contactos encontrados{search_msg}:\n\n"
            
            for i, contact in enumerate(contacts, 1):
                name = contact.get('name', 'Sin nombre')
                jid = contact.get('jid', '')
                
                # Simplificar JID para mostrar
                display_jid = jid.replace('@s.whatsapp.net', '').replace('@g.us', ' (grupo)')
                
                text += f"{i}. {name}\n"
                text += f"   📱 {display_jid}\n\n"
            
            return text
            
        except Exception as e:
            return f"❌ Error listando contactos: {str(e)}"

    def send_message_smart(self, recipient: str, content: str) -> str:
        """Enviar mensaje inteligente"""
        try:
            recipient = recipient.strip()
            content = content.strip()
            
            if not recipient or not content:
                return "❌ Error: Se requieren destinatario y contenido"
            
            # Si ya es un JID completo, enviar directamente
            if "@s.whatsapp.net" in recipient or "@g.us" in recipient:
                result = self._make_request("POST", "/messages", {
                    "chat_jid": recipient, 
                    "content": content
                })
                
                if result.get("success"):
                    mode = result.get("data", {}).get("mode", "unknown")
                    return f"✅ Mensaje enviado a {recipient}\n💬 '{content}'\n🔧 Modo: {mode}"
                else:
                    return f"❌ Error enviando mensaje: {result.get('error', 'Unknown error')}"
            
            # Buscar contacto por nombre
            contacts_result = self._make_request("GET", "/contacts", {"search": recipient})
            contacts = contacts_result.get("data", [])
            
            if not contacts:
                # Intentar como número de teléfono
                if recipient.replace('+', '').replace(' ', '').replace('-', '').isdigit():
                    # Formato como número de WhatsApp
                    clean_number = recipient.replace('+', '').replace(' ', '').replace('-', '')
                    if not clean_number.startswith('549'):
                        if clean_number.startswith('9'):
                            clean_number = '54' + clean_number
                        else:
                            clean_number = '549' + clean_number
                    
                    jid = f"{clean_number}@s.whatsapp.net"
                    result = self._make_request("POST", "/messages", {
                        "chat_jid": jid, 
                        "content": content
                    })
                    
                    if result.get("success"):
                        mode = result.get("data", {}).get("mode", "unknown")
                        return f"✅ Mensaje enviado al número {recipient}\n💬 '{content}'\n🔧 Modo: {mode}"
                    else:
                        return f"❌ Error enviando mensaje al número: {result.get('error', 'Unknown error')}"
                
                return f"❌ No se encontró contacto: '{recipient}'"
            
            elif len(contacts) > 1:
                text = f"🔍 Se encontraron múltiples contactos para '{recipient}':\n\n"
                for i, contact in enumerate(contacts, 1):
                    name = contact.get('name', 'Sin nombre')
                    jid = contact.get('jid', '').replace('@s.whatsapp.net', '')
                    text += f"{i}. {name} ({jid})\n"
                text += "\nSé más específico con el nombre o usa el número directamente."
                return text
            
            else:
                # Contacto único encontrado
                contact = contacts[0]
                chat_jid = contact.get('jid')
                contact_name = contact.get('name', 'Sin nombre')
                
                send_result = self._make_request("POST", "/messages", {
                    "chat_jid": chat_jid, 
                    "content": content
                })
                
                if send_result.get("success"):
                    mode = send_result.get("data", {}).get("mode", "unknown")
                    return f"✅ Mensaje enviado a {contact_name}\n💬 '{content}'\n📱 {chat_jid.replace('@s.whatsapp.net', '')}\n🔧 Modo: {mode}"
                else:
                    return f"❌ Error enviando mensaje: {send_result.get('error', 'Unknown error')}"
            
        except Exception as e:
            return f"❌ Error enviando mensaje: {str(e)}"

    def get_chats(self) -> str:
        """Obtener lista de chats"""
        try:
            result = self._make_request("GET", "/chats")
            chats = result.get("data", [])
            
            if not chats:
                return "💬 No hay chats disponibles"
            
            text = f"💬 Chats activos ({len(chats)}):\n\n"
            
            for i, chat in enumerate(chats, 1):
                chat_jid = chat.get('chat_jid', '')
                message_count = chat.get('message_count', 0)
                last_message = chat.get('last_message', '')
                
                # Simplificar JID para mostrar
                display_jid = chat_jid.replace('@s.whatsapp.net', '').replace('@g.us', ' (grupo)')
                
                text += f"{i}. {display_jid}\n"
                text += f"   📊 {message_count} mensajes\n"
                text += f"   🕐 Último: {last_message}\n\n"
            
            return text
            
        except Exception as e:
            return f"❌ Error obteniendo chats: {str(e)}"

def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Manejar petición MCP"""
    mcp = WhatsAppMCP()
    request_id = request.get("id", 0)
    
    # Manejo de inicialización
    if request.get("method") == "initialize":
        return {
            "jsonrpc": "2.0", 
            "id": request_id, 
            "result": {
                "protocolVersion": "2024-11-05", 
                "capabilities": {"tools": {}}, 
                "serverInfo": {
                    "name": "whatsapp-mcp-secure", 
                    "version": "2.0.0"
                }
            }
        }
    
    # Listar herramientas disponibles
    elif request.get("method") == "tools/list":
        return {
            "jsonrpc": "2.0", 
            "id": request_id, 
            "result": {
                "tools": list(TOOLS_SCHEMA.values())
            }
        }
    
    # Ejecutar herramienta
    elif request.get("method") == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        try:
            if tool_name == "get_health":
                text = mcp.get_health()
            
            elif tool_name == "list_messages":
                limit = tool_args.get("limit", 5)
                text = mcp.list_messages(limit)
            
            elif tool_name == "list_contacts":
                search_query = tool_args.get("search", "")
                text = mcp.list_contacts(search_query)
            
            elif tool_name == "send_message_smart":
                recipient = tool_args.get("recipient", "").strip()
                content = tool_args.get("content", "").strip()
                text = mcp.send_message_smart(recipient, content)
            
            elif tool_name == "get_chats":
                text = mcp.get_chats()
            
            else:
                return mcp._create_error_response(request_id, f"Herramienta desconocida: {tool_name}")
            
            return mcp._create_response(request_id, text)
        
        except Exception as e:
            return mcp._create_error_response(request_id, f"Error ejecutando {tool_name}: {str(e)}")
    
    # Método no reconocido
    return {
        "jsonrpc": "2.0", 
        "id": request_id, 
        "error": {
            "code": -32601, 
            "message": "Method not found"
        }
    }

def main():
    """Función principal del servidor MCP"""
    # Verificar conexión con el bridge al iniciar
    try:
        mcp = WhatsAppMCP()
        result = mcp._make_request("GET", "/health", timeout=5)
        connected = result.get('data', {}).get('connected', False)
        status_msg = "conectado ✅" if connected else "desconectado ❌"
        print(f"[MCP] Bridge verificado: {status_msg}", file=sys.stderr)
    except Exception as e:
        print(f"[MCP] Error verificando bridge: {e}", file=sys.stderr)
        print(f"[MCP] Continuando... (el bridge puede estar iniciándose)", file=sys.stderr)
    
    print("[MCP] Servidor WhatsApp MCP iniciado", file=sys.stderr)
    print("[MCP] Esperando peticiones...", file=sys.stderr)
    
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parsear petición JSON
                request = json.loads(line)
                
                # Procesar petición
                response = handle_mcp_request(request)
                
                # Enviar respuesta
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                print(f"[MCP] Error JSON: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"[MCP] Error procesando petición: {e}", file=sys.stderr)
                continue
                
    except KeyboardInterrupt:
        print("[MCP] Servidor detenido por usuario", file=sys.stderr)
    except Exception as e:
        print(f"[MCP] Error fatal: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
