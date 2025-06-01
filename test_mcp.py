#!/usr/bin/env python3
"""
Script de prueba para verificar que el MCP de WhatsApp funciona
"""

import requests
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(".env")

def test_whatsapp_mcp():
    bridge_url = f"http://{os.getenv('MCP_HOST', '127.0.0.1')}:{os.getenv('BRIDGE_PORT', '8081')}"
    admin_token = os.getenv('ADMIN_TOKEN')
    
    if not admin_token:
        print("Error: ADMIN_TOKEN no está configurado en las variables de entorno")
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    print("🧪 PROBANDO WhatsApp MCP...")
    print("=" * 50)
    
    # 1. Probar salud del sistema
    print("\n1️⃣ Verificando salud del bridge...")
    try:
        response = requests.get(f"{bridge_url}/api/v1/health", headers=headers)
        data = response.json()
        if data.get("success"):
            health = data.get("data", {})
            print(f"   ✅ Estado: {health.get('status')}")
            print(f"   ✅ Conectado: {health.get('connected')}")
            print(f"   ✅ Modo: {health.get('mode')}")
            print(f"   ✅ Mensajes: {health.get('messages_count')}")
        else:
            print(f"   ❌ Error: {data.get('error')}")
            return False
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    # 2. Probar obtener mensajes
    print("\n2️⃣ Obteniendo mensajes recientes...")
    try:
        response = requests.get(f"{bridge_url}/api/v1/messages?limit=3", headers=headers)
        data = response.json()
        if data.get("success"):
            messages = data.get("data", [])
            print(f"   ✅ Se obtuvieron {len(messages)} mensajes")
            for i, msg in enumerate(messages[:2], 1):
                sender = msg.get('sender_jid', 'Unknown')[:20] + "..."
                content = msg.get('content', '')[:30] + "..."
                print(f"   📱 Mensaje {i}: {sender} -> {content}")
        else:
            print(f"   ❌ Error obteniendo mensajes: {data.get('error')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Probar obtener contactos
    print("\n3️⃣ Obteniendo contactos...")
    try:
        response = requests.get(f"{bridge_url}/api/v1/contacts", headers=headers)
        data = response.json()
        if data.get("success"):
            contacts = data.get("data", [])
            print(f"   ✅ Se encontraron {len(contacts)} contactos")
            for i, contact in enumerate(contacts[:3], 1):
                name = contact.get('name', 'Sin nombre')
                jid = contact.get('jid', '')[:20] + "..."
                print(f"   👤 Contacto {i}: {name} ({jid})")
        else:
            print(f"   ❌ Error obteniendo contactos: {data.get('error')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Probar obtener chats
    print("\n4️⃣ Obteniendo chats...")
    try:
        response = requests.get(f"{bridge_url}/api/v1/chats", headers=headers)
        data = response.json()
        if data.get("success"):
            chats = data.get("data", [])
            print(f"   ✅ Se encontraron {len(chats)} chats activos")
            for i, chat in enumerate(chats[:3], 1):
                chat_jid = chat.get('chat_jid', '')[:30] + "..."
                msg_count = chat.get('message_count', 0)
                print(f"   💬 Chat {i}: {chat_jid} ({msg_count} mensajes)")
        else:
            print(f"   ❌ Error obteniendo chats: {data.get('error')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 PRUEBA")#prueba exitosa