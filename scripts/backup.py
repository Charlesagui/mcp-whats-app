#!/usr/bin/env python3
"""
Script de backup seguro para WhatsApp MCP
Crea backups cifrados de la base de datos y archivos de configuración
"""

import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from cryptography.fernet import Fernet
import json
from dotenv import load_dotenv

class SecureBackup:
    def __init__(self):
        load_dotenv("../.env")
        self.backup_key = os.getenv('BACKUP_ENCRYPTION_KEY')
        self.backup_path = os.getenv('BACKUP_PATH', '../backups')
        self.data_path = os.getenv('DB_PATH', '../data/whatsapp_secure.db')
        
        if not self.backup_key:
            raise ValueError("BACKUP_ENCRYPTION_KEY no configurada")
        
        self.fernet = Fernet(self.backup_key.encode()[:44] + b'=')
        
        # Crear directorio de backups si no existe
        os.makedirs(self.backup_path, exist_ok=True)
    
    def create_backup(self):
        """Crear backup completo cifrado"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"whatsapp_backup_{timestamp}"
        temp_dir = f"/tmp/{backup_name}"
        
        try:
            # Crear directorio temporal
            os.makedirs(temp_dir, exist_ok=True)
            
            # Copiar base de datos
            if os.path.exists(self.data_path):
                shutil.copy2(self.data_path, f"{temp_dir}/database.db")
            
            # Copiar archivos de autenticación
            auth_dir = "../auth"
            if os.path.exists(auth_dir):
                shutil.copytree(auth_dir, f"{temp_dir}/auth")
            
            # Crear archivo de metadatos
            metadata = {
                "timestamp": timestamp,
                "version": "1.0",
                "database_size": os.path.getsize(self.data_path) if os.path.exists(self.data_path) else 0,
                "created_by": "WhatsApp MCP Secure"
            }
            
            with open(f"{temp_dir}/metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Crear archivo ZIP
            zip_path = f"{temp_dir}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arc_path)
            
            # Cifrar backup
            with open(zip_path, 'rb') as f:
                encrypted_data = self.fernet.encrypt(f.read())
            
            # Guardar backup cifrado
            backup_file = f"{self.backup_path}/{backup_name}.backup"
            with open(backup_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Limpiar archivos temporales
            shutil.rmtree(temp_dir)
            os.remove(zip_path)
            
            print(f"✓ Backup creado: {backup_file}")
            return backup_file
            
        except Exception as e:
            print(f"✗ Error creando backup: {e}")
            # Limpiar en caso de error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return None
    
    def restore_backup(self, backup_file):
        """Restaurar backup cifrado"""
        if not os.path.exists(backup_file):
            print(f"✗ Archivo de backup no encontrado: {backup_file}")
            return False
        
        try:
            # Leer y descifrar backup
            with open(backup_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # Crear archivo temporal
            temp_zip = f"/tmp/restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            with open(temp_zip, 'wb') as f:
                f.write(decrypted_data)
            
            # Extraer archivos
            extract_dir = f"/tmp/extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with zipfile.ZipFile(temp_zip, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            # Restaurar archivos
            if os.path.exists(f"{extract_dir}/database.db"):
                shutil.copy2(f"{extract_dir}/database.db", self.data_path)
                print("✓ Base de datos restaurada")
            
            if os.path.exists(f"{extract_dir}/auth"):
                auth_dir = "../auth"
                if os.path.exists(auth_dir):
                    shutil.rmtree(auth_dir)
                shutil.copytree(f"{extract_dir}/auth", auth_dir)
                print("✓ Archivos de autenticación restaurados")
            
            # Limpiar archivos temporales
            os.remove(temp_zip)
            shutil.rmtree(extract_dir)
            
            print("✓ Backup restaurado correctamente")
            return True
            
        except Exception as e:
            print(f"✗ Error restaurando backup: {e}")
            return False
    
    def list_backups(self):
        """Listar backups disponibles"""
        if not os.path.exists(self.backup_path):
            print("No hay backups disponibles")
            return []
        
        backups = []
        for file in os.listdir(self.backup_path):
            if file.endswith('.backup'):
                file_path = os.path.join(self.backup_path, file)
                size = os.path.getsize(file_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                backups.append({
                    'file': file,
                    'path': file_path,
                    'size': size,
                    'modified': mtime
                })
        
        backups.sort(key=lambda x: x['modified'], reverse=True)
        
        print(f"Backups disponibles ({len(backups)}):")
        for backup in backups:
            size_mb = backup['size'] / (1024 * 1024)
            print(f"  • {backup['file']} ({size_mb:.1f} MB) - {backup['modified']}")
        
        return backups

def main():
    import sys
    
    backup = SecureBackup()
    
    if len(sys.argv) < 2:
        print("Uso: python backup.py [create|restore|list]")
        print("  create           - Crear nuevo backup")
        print("  restore <file>   - Restaurar backup")
        print("  list             - Listar backups disponibles")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        backup.create_backup()
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Especifica el archivo de backup a restaurar")
            sys.exit(1)
        backup.restore_backup(sys.argv[2])
    elif command == "list":
        backup.list_backups()
    else:
        print(f"Comando desconocido: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
