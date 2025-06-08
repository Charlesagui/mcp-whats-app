#!/usr/bin/env python3
"""Configurador simple de Claude Desktop para WhatsApp MCP"""

import json
import os
import sys

def find_claude_config():
    """Encuentra el archivo de configuracion de Claude Desktop"""
    # Ruta estandar de Windows
    config_dir = os.path.expanduser("~\\AppData\\Roaming\\Claude")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "claude_desktop_config.json")

def get_project_path():
    """Obtiene la ruta del proyecto actual"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)  # Subir un nivel desde mcp-server

def main():
    print("Configurador de Claude Desktop para WhatsApp MCP")
    print("=" * 50)
    
    # Encontrar archivo de configuracion
    config_path = find_claude_config()
    print(f"Archivo de configuracion: {config_path}")
    
    # Cargar configuracion existente o crear nueva
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("Configuracion existente cargada")
        except Exception as e:
            print(f"Error cargando configuracion existente: {e}")
            config = {}
    else:
        print("Creando nueva configuracion")
    
    # Asegurar estructura MCP
    if 'mcpServers' not in config:
        config['mcpServers'] = {}
    
    # Configuracion del servidor WhatsApp MCP
    project_path = get_project_path()
    mcp_script_path = os.path.join(project_path, "mcp-server", "main_fixed.py")
    
    config['mcpServers']['whatsapp-mcp-secure'] = {
        "command": "python",
        "args": [mcp_script_path],
        "env": {
            "PYTHONPATH": os.path.join(project_path, "mcp-server")
        }
    }
    
    # Guardar configuracion
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("Configuracion guardada exitosamente")
        print(f"Ruta del script: {mcp_script_path}")
        print()
        print("IMPORTANTE: Reinicia Claude Desktop para aplicar los cambios")
        print()
        print("Configuracion aplicada:")
        print(f"   • Servidor: whatsapp-mcp-secure")
        print(f"   • Comando: python {mcp_script_path}")
        print()
        print("Para probar, usa en Claude:")
        print('   "Cual es el estado de WhatsApp?"')
        print('   "Envia un WhatsApp a [nombre] diciendo [mensaje]"')
        print('   "Muestra mis contactos de WhatsApp"')
        
    except Exception as e:
        print(f"Error guardando configuracion: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if main():
        print("\nConfiguracion completada exitosamente!")
    else:
        print("\nError en la configuracion")
        sys.exit(1)
