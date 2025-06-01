#!/usr/bin/env python3
"""WhatsApp MCP Server - Versión optimizada"""
import json, sys, os, urllib.request, urllib.parse, urllib.error

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

# Esquemas de herramientas
TOOLS_SCHEMA = {
    "get_health": {
        "name": "get_health", 
        "description": "Ver estado de WhatsApp", 
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}
    },
    "list_messages": {
        "name": "list_messages", 
        "description": "Listar mensajes", 
        "inputSchema": {
            "type": "object", 
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}}, 
            "additionalProperties": False
        }
    },
    "list_contacts": {
        "name": "list_contacts", 
        "description": "Listar contactos", 
        "inputSchema": {
            "type": "object", 
            "properties": {"search": {"type": "string"}}, 
            "additionalProperties": False
        }
    },
    "send_message_smart": {
        "name": "send_message_smart", 
        "description": "Enviar mensaje por nombre o numero", 
        "inputSchema": {
            "type": "object", 
            "properties": {"recipient": {"type": "string"}, "content": {"type": "string"}}, 
            "required": ["recipient", "content"], 
            "additionalProperties": False
        }
    }
}

class WhatsAppMCP:
    def __init__(self):
        host = os.getenv('MCP_HOST', '127.0.0.1')
        port = os.getenv('BRIDGE_PORT', '8081')
        self.bridge_url = f"http://{host}:{port}"
        
        self.admin_token = os.getenv('ADMIN_TOKEN')
        if not self.admin_token:
            raise ValueError("ADMIN_TOKEN no está configurado")
        
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.bridge_url}/api/v1{endpoint}"
        headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
        
        if method == "GET" and data:
            url += f"?{urllib.parse.urlencode(data)}"
            data = None
        elif data:
            data = json.dumps(data).encode('utf-8')
        
        try:
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise Exception(f"Error conectando a WhatsApp: {str(e)}")

    def _create_response(self, request_id, content):
        """Crear respuesta MCP estándar"""
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": content}]}}

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
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": list(TOOLS_SCHEMA.values())}}
    
    elif request.get("method") == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        try:
            if tool_name == "get_health":
                result = mcp._make_request("GET", "/health")
                health = result.get("data", {})
                text = f"Estado WhatsApp: {health.get('status')}, Conectado: {'Si' if health.get('connected') else 'No'}, Mensajes: {health.get('messages_count')}"
            
            elif tool_name == "list_messages":
                limit = max(1, min(tool_args.get("limit", 5), 50))
                result = mcp._make_request("GET", "/messages", {"limit": limit})
                messages = result.get("data", [])
                
                if not messages:
                    text = "No hay mensajes"
                else:
                    text = f"Ultimos {len(messages)} mensajes:\n"
                    for i, msg in enumerate(messages, 1):
                        content = msg.get('content', '')
                        content = content[:80] + ("..." if len(content) > 80 else "")
                        text += f"{i}. {msg.get('sender_jid')}: {content}\n"
            
            elif tool_name == "list_contacts":
                search_query = tool_args.get("search", "")
                params = {"search": search_query} if search_query else {}
                result = mcp._make_request("GET", "/contacts", params)
                contacts = result.get("data", [])
                
                if not contacts:
                    text = "No hay contactos disponibles"
                else:
                    text = "Contactos encontrados:\n"
                    for i, contact in enumerate(contacts, 1):
                        text += f"{i}. {contact.get('name')}: {contact.get('jid')}\n"
            
            elif tool_name == "send_message_smart":
                recipient = tool_args.get("recipient", "").strip()
                content = tool_args.get("content", "").strip()
                
                if not recipient or not content:
                    text = "Error: Se requieren recipient y content"
                elif "@s.whatsapp.net" in recipient:
                    # Es numero directo
                    result = mcp._make_request("POST", "/messages", {"chat_jid": recipient, "content": content})
                    text = f"Mensaje enviado a {recipient}: {content}" if result.get("success") else f"Error enviando mensaje: {result.get('error')}"
                else:
                    # Buscar contacto
                    contacts_result = mcp._make_request("GET", "/contacts", {"search": recipient})
                    contacts = contacts_result.get("data", [])
                    
                    if not contacts:
                        text = f"No se encontro contacto: {recipient}"
                    elif len(contacts) > 1:
                        text = f"Multiples contactos encontrados para '{recipient}'. Se mas especifico."
                    else:
                        contact = contacts[0]
                        chat_jid = contact.get('jid')
                        send_result = mcp._make_request("POST", "/messages", {"chat_jid": chat_jid, "content": content})
                        text = f"Mensaje enviado a {contact.get('name')} ({chat_jid}): {content}" if send_result.get("success") else f"Error enviando mensaje: {send_result.get('error')}"
            else:
                text = f"Herramienta desconocida: {tool_name}"
            
            return mcp._create_response(request_id, text)
        
        except Exception as e:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -1, "message": f"Error: {str(e)}"}}
    
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}

def main():
    try:
        mcp = WhatsAppMCP()
        result = mcp._make_request("GET", "/health")
        print(f"Bridge OK, conectado: {result.get('data', {}).get('connected')}", file=sys.stderr)
    except Exception as e:
        print(f"Error bridge: {e}", file=sys.stderr)
    
    try:
        while True:
            line = sys.stdin.readline()
            if not line: break
            line = line.strip()
            if not line: continue
            
            try:
                request = json.loads(line)
                response = handle_mcp_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
