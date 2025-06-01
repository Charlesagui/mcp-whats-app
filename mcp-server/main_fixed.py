#!/usr/bin/env python3
"""
WhatsApp MCP Server - Versión corregida para Claude Desktop
"""

import asyncio
import sys
import signal
from main import WhatsAppMCPServer

def signal_handler(signum, frame):
    print("\nServidor detenido por el usuario")
    sys.exit(0)

def run_server():
    """Ejecutar el servidor MCP de forma robusta"""
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Crear el servidor
        server = WhatsAppMCPServer()
        
        # Verificar si hay un loop de asyncio corriendo
        try:
            loop = asyncio.get_running_loop()
            print("Loop de asyncio ya está corriendo")
            # Crear una nueva instancia del loop
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(server.run())
        except RuntimeError:
            # No hay loop corriendo, usar asyncio.run()
            asyncio.run(server.run())
            
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()
