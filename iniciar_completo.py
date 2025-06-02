#!/usr/bin/env python3
"""Iniciador completo de WhatsApp MCP - Version Python"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

class WhatsAppMCPLauncher:
    def __init__(self):
        self.project_path = Path("C:/Users/aguia/mcp-whats-app")
        self.bridge_path = self.project_path / "whatsapp-bridge"
        self.mcp_path = self.project_path / "mcp-server"
        self.bridge_process = None
        self.mcp_process = None
        
    def print_header(self):
        print("\n" + "="*50)
        print("     WHATSAPP MCP - INICIADOR COMPLETO")
        print("="*50 + "\n")
        
    def verify_project(self):
        """Verificar que el proyecto existe"""
        if not (self.project_path / ".env").exists():
            print("❌ Error: Proyecto no encontrado")
            print(f"Verifica la ruta: {self.project_path}")
            return False
        print("✅ Proyecto encontrado")
        return True
        
    def verify_dependencies(self):
        """Verificar dependencias"""
        print("🔍 Verificando dependencias...")
        
        # Verificar Go
        try:
            subprocess.run(["go", "version"], capture_output=True, check=True)
        except:
            print("❌ Go no instalado")
            return False
            
        # Verificar Python
        try:
            subprocess.run([sys.executable, "--version"], capture_output=True, check=True)
        except:
            print("❌ Python no instalado")
            return False
            
        print("✅ Dependencias verificadas")
        return True
        
    def create_directories(self):
        """Crear directorios necesarios"""
        (self.project_path / "logs").mkdir(exist_ok=True)
        (self.project_path / "data").mkdir(exist_ok=True)
        
    def kill_previous_processes(self):
        """Matar procesos previos"""
        print("🧹 Limpiando procesos previos...")
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(["taskkill", "/f", "/im", "whatsapp-bridge.exe"], 
                             capture_output=True)
                subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                             capture_output=True)
        except:
            pass
        time.sleep(2)
        
    def compile_bridge(self):
        """Compilar bridge si es necesario"""
        bridge_exe = self.bridge_path / "whatsapp-bridge.exe"
        
        if not bridge_exe.exists():
            print("🔨 Compilando WhatsApp Bridge...")
            try:
                env = os.environ.copy()
                env["CGO_ENABLED"] = "1"
                
                result = subprocess.run(
                    ["go", "build", "-o", "whatsapp-bridge.exe", "."],
                    cwd=self.bridge_path,
                    env=env,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print("❌ Error compilando bridge:")
                    print(result.stderr)
                    return False
                    
                print("✅ Bridge compilado exitosamente")
            except Exception as e:
                print(f"❌ Error compilando: {e}")
                return False
        else:
            print("✅ Bridge ya existe")
            
        return True
        
    def start_bridge(self):
        """Iniciar WhatsApp Bridge"""
        print("📱 Iniciando WhatsApp Bridge...")
        
        bridge_exe = self.bridge_path / "whatsapp-bridge.exe"
        
        if os.name == 'nt':  # Windows
            # Crear ventana separada en Windows
            subprocess.Popen([
                "cmd", "/c", "start", 
                "🔗 WhatsApp Bridge - Puerto 8081",
                "cmd", "/k", 
                f"cd {self.bridge_path} && echo 📱 WHATSAPP BRIDGE INICIADO && echo Esperando conexion... && echo. && whatsapp-bridge.exe"
            ], shell=True)
        else:
            # Para Linux/Mac
            self.bridge_process = subprocess.Popen(
                [str(bridge_exe)],
                cwd=self.bridge_path
            )
            
        return True
        
    def start_mcp_server(self):
        """Iniciar MCP Server"""
        print("🤖 Iniciando MCP Server...")
        
        main_script = self.mcp_path / "main_fixed.py"
        
        if os.name == 'nt':  # Windows
            # Crear ventana separada en Windows
            subprocess.Popen([
                "cmd", "/c", "start",
                "🔧 MCP Server - Puerto 8080", 
                "cmd", "/k",
                f"cd {self.mcp_path} && echo 🤖 MCP SERVER INICIADO && echo Conectando con Claude Desktop... && echo. && python main_fixed.py"
            ], shell=True)
        else:
            # Para Linux/Mac
            self.mcp_process = subprocess.Popen(
                [sys.executable, str(main_script)],
                cwd=self.mcp_path
            )
            
        return True
        
    def configure_claude(self):
        """Configurar Claude Desktop"""
        print("\n🔧 Configurando Claude Desktop...")
        try:
            result = subprocess.run(
                [sys.executable, "configure_claude_simple.py"],
                cwd=self.mcp_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Claude Desktop configurado")
                print("🔄 REINICIA CLAUDE DESKTOP PARA APLICAR CAMBIOS")
                return True
            else:
                print("❌ Error configurando Claude Desktop")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
            
    def show_instructions(self):
        """Mostrar instrucciones finales"""
        print("\n✅ SERVICIOS INICIADOS CORRECTAMENTE\n")
        print("📋 ESTADO:")
        print("   🔗 WhatsApp Bridge: Puerto 8081 (ventana separada)")
        print("   🤖 MCP Server:      Puerto 8080 (ventana separada)")
        print("\n📱 CONECTAR WHATSAPP:")
        print("   1. Ve a la ventana 'WhatsApp Bridge - Puerto 8081'")
        print("   2. Escanea el código QR con tu teléfono:")
        print("      • WhatsApp > Dispositivos Vinculados")
        print("      • 'Vincular un dispositivo'")
        print("      • Escanear el QR visual")
        print("\n🔧 EN CLAUDE DESKTOP:")
        print("   3. Reinicia Claude Desktop")
        print("   4. Prueba: '¿Cuál es el estado de WhatsApp?'")
        
    def cleanup(self, signum=None, frame=None):
        """Limpiar procesos al salir"""
        print("\n🛑 Deteniendo servicios...")
        
        if self.bridge_process:
            self.bridge_process.terminate()
        if self.mcp_process:
            self.mcp_process.terminate()
            
        sys.exit(0)
        
    def run(self):
        """Ejecutar el iniciador completo"""
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        try:
            self.print_header()
            
            if not self.verify_project():
                return False
                
            if not self.verify_dependencies():
                return False
                
            self.create_directories()
            self.kill_previous_processes()
            
            if not self.compile_bridge():
                return False
                
            print("\n🚀 Iniciando servicios...\n")
            
            if not self.start_bridge():
                return False
                
            time.sleep(3)  # Esperar que el bridge inicie
            
            if not self.start_mcp_server():
                return False
                
            time.sleep(2)  # Esperar que el MCP inicie
            
            self.configure_claude()
            self.show_instructions()
            
            # Mantener el script corriendo
            print("\n⌨️  Presiona Ctrl+C para detener todos los servicios")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.cleanup()
                
            return True
            
        except Exception as e:
            print(f"❌ Error fatal: {e}")
            return False

if __name__ == "__main__":
    launcher = WhatsAppMCPLauncher()
    success = launcher.run()
    
    if not success:
        print("\n❌ Error en el iniciador")
        sys.exit(1)
