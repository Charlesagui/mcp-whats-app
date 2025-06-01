#!/usr/bin/env python3
"""WhatsApp MCP Server - Versión funcional"""
import json, sys, os, urllib.request, urllib.parse, urllib.error

class WhatsAppMCP:
    def __init__(self):
        self.bridge_url = "http://127.0.0.1:8081"
        self.admin_token = "c80502a4c4594f6730bc320274a289847ac29e02a627e866a8066d768a081c77"
        
    def _make_request(self, method, endpoint, data=None):
        try:
            url = f"{self.bridge_url}/api/v1{endpoint}"
            headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
            
            if method.upper() == "GET" and data:
                query_string = urllib.parse.urlencode(data)
                url = f"{url}?{query_string}"
                req_data = None
            elif method.upper() == "POST" and data:
                req_data = json.dumps(data).encode('utf-8')
            else:
                req_data = None
            
            request = urllib.request.Request(url, data=req_data, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
                
        except Exception as e:
            raise Exception(f"Error conectando a WhatsApp: {str(e)}")

def handle_mcp_request(request):
    mcp = WhatsAppMCP()
    request_id = request.get("id", 0)
    
    if request.get("method") == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "whatsapp-secure", "version": "1.0.0"}}}
    
    elif request.get("method") == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": [
            {"name": "get_health", "description": "Ver estado de WhatsApp", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
            {"name": "list_messages", "description": "Listar mensajes", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "additionalProperties": False}},
            {"name": "list_contacts", "description": "Listar contactos", "inputSchema": {"type": "object", "properties": {"search": {"type": "string"}}, "additionalProperties": False}},
            {"name": "send_message_smart", "description": "Enviar mensaje por nombre o numero", "inputSchema": {"type": "object", "properties": {"recipient": {"type": "string"}, "content": {"type": "string"}}, "required": ["recipient", "content"], "additionalProperties": False}}
        ]}}
    
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
                limit = min(max(tool_args.get("limit", 5), 1), 50)
                result = mcp._make_request("GET", "/messages", {"limit": limit})
                messages = result.get("data", [])
                if messages:
                    text = f"Ultimos {len(messages)} mensajes:\n"
                    for i, msg in enumerate(messages, 1):
                        content = msg.get('content', '')[:80] + ("..." if len(msg.get('content', '')) > 80 else "")
                        text += f"{i}. {msg.get('sender_jid')}: {content}\n"
                else:
                    text = "No hay mensajes"
            
            elif tool_name == "list_contacts":
                search_query = tool_args.get("search", "")
                search_data = {"search": search_query} if search_query else {}
                result = mcp._make_request("GET", "/contacts", search_data)
                contacts = result.get("data", [])
                if contacts:
                    text = f"Contactos encontrados:\n"
                    for i, contact in enumerate(contacts, 1):
                        text += f"{i}. {contact.get('name')}: {contact.get('jid')}\n"
                else:
                    text = "No hay contactos disponibles"
            
            elif tool_name == "send_message_smart":
                recipient = tool_args.get("recipient", "").strip()
                content = tool_args.get("content", "").strip()
                
                if not recipient or not content:
                    text = "Error: Se requieren recipient y content"
                elif "@s.whatsapp.net" in recipient:
                    # Es numero directo
                    result = mcp._make_request("POST", "/messages", {"chat_jid": recipient, "content": content})
                    if result.get("success"):
                        text = f"Mensaje enviado a {recipient}: {content}"
                    else:
                        text = f"Error enviando mensaje: {result.get('error')}"
                else:
                    # Buscar contacto
                    contacts_result = mcp._make_request("GET", "/contacts", {"search": recipient})
                    contacts = contacts_result.get("data", [])
                    
                    if not contacts:
                        text = f"No se encontro contacto: {recipient}"
                    elif len(contacts) == 1:
                        contact = contacts[0]
                        chat_jid = contact.get('jid')
                        send_result = mcp._make_request("POST", "/messages", {"chat_jid": chat_jid, "content": content})
                        if send_result.get("success"):
                            text = f"Mensaje enviado a {contact.get('name')} ({chat_jid}): {content}"
                        else:
                            text = f"Error enviando mensaje: {send_result.get('error')}"
                    else:
                        text = f"Multiples contactos encontrados para '{recipient}'. Se mas especifico."
            else:
                text = f"Herramienta desconocida: {tool_name}"
            
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": text}]}}
        
        except Exception as e:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -1, "message": f"Error: {str(e)}"}}
    
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}

def main():
    print("WhatsApp MCP iniciado", file=sys.stderr)
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
