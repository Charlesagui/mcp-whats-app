#!/usr/bin/env python3
"""
WhatsApp MCP Server - Servidor MCP seguro para WhatsApp
Implementa el Model Context Protocol para interactuar con WhatsApp de forma segura.
"""

import asyncio
import os
import sys
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from fastmcp import FastMCP
from pydantic import BaseModel
import requests
from loguru import logger
from dotenv import load_dotenv
import aiofiles

# Cargar variables de entorno
load_dotenv("../.env")

class WhatsAppMCPServer:
    def __init__(self):
        self.bridge_url = f"http://{os.getenv('MCP_HOST', '127.0.0.1')}:{os.getenv('BRIDGE_PORT', '8081')}"
        self.admin_token = os.getenv('ADMIN_TOKEN', 'default_admin_token')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Configurar logging
        logger.remove()
        logger.add(
            sys.stderr,
            level=self.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # Configurar logging a archivo
        log_path = os.getenv('LOG_PATH', '../logs')
        os.makedirs(log_path, exist_ok=True)
        logger.add(
            f"{log_path}/mcp_server.log",
            rotation="1 day",
            retention="30 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        self.mcp = FastMCP("WhatsApp MCP Secure")
        self._setup_tools()
        
    def _get_headers(self) -> Dict[str, str]:
        """Obtener headers de autenticación para el bridge"""
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
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
            logger.error(f"Error en solicitud HTTP: {e}")
            raise Exception(f"Error comunicándose con WhatsApp bridge: {str(e)}")
    
    def _setup_tools(self):
        """Configurar las herramientas MCP"""
        
        @self.mcp.tool()
        async def search_contacts(query: str) -> str:
            """
            Buscar contactos por nombre o número de teléfono.
            
            Args:
                query: Texto a buscar en nombres o números de contactos
            """
            try:
                result = await self._make_request("GET", "/contacts", {"search": query})
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
                logger.error(f"Error buscando contactos: {e}")
                return f"Error buscando contactos: {str(e)}"
        
        @self.mcp.tool()
        async def list_messages(chat_jid: str = "", limit: int = 50) -> str:
            """
            Listar mensajes de WhatsApp.
            
            Args:
                chat_jid: ID del chat (opcional, si no se especifica lista todos)
                limit: Número máximo de mensajes a obtener (default: 50)
            """
            try:
                params = {"limit": limit}
                if chat_jid:
                    params["chat_jid"] = chat_jid
                
                result = await self._make_request("GET", "/messages", params)
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
                logger.error(f"Error obteniendo mensajes: {e}")
                return f"Error obteniendo mensajes: {str(e)}"
        
        @self.mcp.tool()
        async def send_message(chat_jid: str, content: str) -> str:
            """
            Enviar un mensaje de WhatsApp.
            
            Args:
                chat_jid: ID del chat de destino
                content: Contenido del mensaje a enviar
            """
            try:
                data = {
                    "chat_jid": chat_jid,
                    "content": content
                }
                
                result = await self._make_request("POST", "/messages", data)
                if result.get("success"):
                    msg_data = result.get("data", {})
                    return f"Mensaje enviado correctamente. ID: {msg_data.get('message_id', 'N/A')}"
                else:
                    return f"Error enviando mensaje: {result.get('error', 'Error desconocido')}"
            except Exception as e:
                logger.error(f"Error enviando mensaje: {e}")
                return f"Error enviando mensaje: {str(e)}"
        
        @self.mcp.tool()
        async def get_health() -> str:
            """
            Verificar el estado de salud del bridge de WhatsApp.
            """
            try:
                result = await self._make_request("GET", "/health")
                if result.get("success"):
                    health_data = result.get("data", {})
                    status = health_data.get("status", "unknown")
                    connected = health_data.get("connected", False)
                    timestamp = health_data.get("timestamp", "N/A")
                    
                    return f"Estado del bridge: {status}\nConectado a WhatsApp: {connected}\nÚltima verificación: {timestamp}"
                else:
                    return f"Error verificando salud: {result.get('error', 'Error desconocido')}"
            except Exception as e:
                logger.error(f"Error verificando salud: {e}")
                return f"Error verificando salud del bridge: {str(e)}"
    
    async def run(self):
        """Ejecutar el servidor MCP"""
        logger.info("Iniciando WhatsApp MCP Server...")
        
        # Verificar conexión con el bridge
        try:
            await self._make_request("GET", "/health")
            logger.info("Conexión con WhatsApp bridge establecida")
        except Exception as e:
            logger.error(f"No se pudo conectar con WhatsApp bridge: {e}")
            logger.error("Asegúrate de que el bridge esté ejecutándose en el puerto correcto")
            return
        
        # Ejecutar servidor MCP
        try:
            await self.mcp.run()
        except KeyboardInterrupt:
            logger.info("Cerrando WhatsApp MCP Server...")
        except Exception as e:
            logger.error(f"Error en servidor MCP: {e}")

async def main():
    """Función principal"""
    server = WhatsAppMCPServer()
    await server.run()

if __name__ == "__main__":
    try:
        # Verificar si ya hay un loop de asyncio corriendo
        try:
            loop = asyncio.get_running_loop()
            # Si hay un loop corriendo, crear una tarea
            loop.create_task(main())
        except RuntimeError:
            # No hay loop corriendo, usar asyncio.run()
            asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)
