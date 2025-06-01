#!/usr/bin/env python3
"""
Generador de configuración para Claude Desktop
Crea automáticamente el archivo de configuración para integrar WhatsApp MCP
"""

import json
import os
import sys
from pathlib import Path

def get_claude_config_path():
    """Detectar la ruta de configuración de Claude Desktop según el SO"""
    if os.name == 'nt':  # Windows
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == 'darwin':  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"

def create_claude_config():
    """Crear configuración de Claude Desktop"""
    
    # Obtener ruta absoluta del proyecto
    project_path = Path(__file__).parent.parent.absolute()
    python_path = sys.executable
    
    # Verificar que existe el servidor MCP
    mcp_server_path = project_path / "mcp-server" / "main.py"
    if not mcp_server_path.exists():
        print(f"❌ Error: No se encuentra el servidor MCP en {mcp_server_path}")
        return False
    
    # Verificar que existe el entorno virtual
    if os.name == 'nt':
        venv_python = project_path / "mcp-server" / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = project_path / "mcp-server" / "venv" / "bin" / "python"
    
    # Usar Python del entorno virtual si existe, sino el del sistema
    if venv_python.exists():
        python_path = str(venv_python)
        print(f"✅ Usando Python del entorno virtual: {python_path}")
    else:
        print(f"⚠️  Entorno virtual no encontrado, usando Python del sistema: {python_path}")
    
    # Configuración de Claude Desktop
    config = {
        "mcpServers": {
            "whatsapp-secure": {
                "command": python_path,
                "args": [str(mcp_server_path)],
                "env": {
                    "PYTHONPATH": str(project_path / "mcp-server"),
                    "PYTHONUNBUFFERED": "1"
                }
            }
        },
        "globalShortcuts": {
            "assistantToggle": "Ctrl+Shift+Space"
        },
        "defaults": {
            "model": "claude-3-5-sonnet-20241022"
        }
    }
    
    # Obtener ruta de configuración
    config_path = get_claude_config_path()
    
    print(f"📍 Ruta de configuración de Claude: {config_path}")
    
    # Crear directorio si no existe
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Leer configuración existente si existe
    existing_config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            print("✅ Configuración existente encontrada, se actualizará")
        except json.JSONDecodeError:
            print("⚠️  Configuración existente corrupta, se creará nueva")
    
    # Fusionar configuraciones
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["whatsapp-secure"] = config["mcpServers"]["whatsapp-secure"]
    
    # Agregar configuraciones adicionales si no existen
    for key, value in config.items():
        if key != "mcpServers" and key not in existing_config:
            existing_config[key] = value
    
    # Escribir configuración
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Configuración de Claude Desktop actualizada: {config_path}")
        print("\n📋 Próximos pasos:")
        print("1. Reinicia Claude Desktop")
        print("2. Inicia WhatsApp MCP Secure con: scripts/start.bat")
        print("3. En Claude, deberías ver 'whatsapp-secure' como herramienta disponible")
        
        return True
        
    except Exception as e:
        print(f"❌ Error escribiendo configuración: {e}")
        return False

def show_config_info():
    """Mostrar información sobre la configuración actual"""
    config_path = get_claude_config_path()
    
    if not config_path.exists():
        print(f"📍 No existe configuración en: {config_path}")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"📍 Configuración encontrada en: {config_path}")
        
        if "mcpServers" in config:
            servers = config["mcpServers"]
            print(f"🔧 Servidores MCP configurados: {len(servers)}")
            
            for name, server_config in servers.items():
                print(f"  • {name}: {server_config.get('command', 'N/A')}")
                
            if "whatsapp-secure" in servers:
                print("✅ WhatsApp MCP ya está configurado")
            else:
                print("⚠️  WhatsApp MCP no está configurado")
        else:
            print("⚠️  No hay servidores MCP configurados")
            
    except json.JSONDecodeError:
        print("❌ Error: Configuración corrupta")
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")

def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        show_config_info()
    else:
        print("🔧 Configurador de Claude Desktop para WhatsApp MCP Secure")
        print("=" * 60)
        
        if create_claude_config():
            print("\n🎉 ¡Configuración completada exitosamente!")
        else:
            print("\n❌ Error en la configuración")
            sys.exit(1)

if __name__ == "__main__":
    main()
