#!/usr/bin/env python3
"""
WhatsApp MCP Server - Versión simplificada para Claude Desktop
"""

import json
import sys
import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
import os
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

class WhatsAppMCP:
    def __init__(self):
        # Configuración del servidor
        host = os.getenv('MCP_HOST', '127.0.0.1')
        port = os.getenv('BRIDGE_PORT', '8081')
        self.bridge_url = f"http://{host}:{port}"
        
        # Token de administración (obligatorio)
        self.admin_token = os.getenv('ADMIN_TOKEN')
        if not self.admin_token:
            raise ValueError("ADMIN_TOKEN no está configurado en las variables de entorno")
        
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.bridge_url}/api/v1{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data or {})
            else:
                response = requests.post(url, headers=headers, json=data or {})
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error: {str(e)}")

def handle_mcp_request(request):
    mcp = WhatsAppMCP()
    request_id = request.get("id", 0)  # Usar 0 como default en lugar de None
    
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
                        "description": "Verificar estado de WhatsApp",
                        "inputSchema": {
                            "type": "object", 
                            "properties": {},
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "list_messages",
                        "description": "Listar mensajes de WhatsApp",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "description": "Número de mensajes"}
                            },
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
                text = f"Estado: {health.get('status')}\nConectado: {health.get('connected')}\nMensajes: {health.get('messages_count')}"
            
            elif tool_name == "list_messages":
                limit = tool_args.get("limit", 5)
                result = mcp._make_request("GET", "/messages", {"limit": limit})
                messages = result.get("data", [])
                if messages:
                    text = "Últimos mensajes:\n"
                    for msg in messages:
                        text += f"• [{msg['timestamp']}] {msg['sender_jid']}: {msg['content']}\n"
                else:
                    text = "No hay mensajes"
            
            else:
                text = f"Herramienta desconocida: {tool_name}"
            
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
                    "message": str(e)
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
    print("WhatsApp MCP Server iniciado", file=sys.stderr)
    
    # Verificar conexión con el bridge al inicio
    try:
        mcp = WhatsAppMCP()
        result = mcp._make_request("GET", "/health")
        print(f"Bridge conectado: {result.get('data', {}).get('connected')}", file=sys.stderr)
    except Exception as e:
        print(f"Advertencia: No se pudo conectar con el bridge: {e}", file=sys.stderr)
    
    # Loop principal para mantener el servidor vivo
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:  # EOF
                    print("EOF recibido, cerrando servidor", file=sys.stderr)
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                print(f"Procesando: {line[:50]}...", file=sys.stderr)
                request = json.loads(line)
                response = handle_mcp_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
                print(f"Respondido método: {request.get('method')}", file=sys.stderr)
                
            except json.JSONDecodeError as e:
                print(f"Error JSON: {e}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"Error procesando: {e}", file=sys.stderr)
                continue
                
    except EOFError:
        print("Cliente desconectado", file=sys.stderr)
    except KeyboardInterrupt:
        print("Servidor detenido por usuario", file=sys.stderr)
    except Exception as e:
        print(f"Error fatal: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
