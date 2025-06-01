# 🚀 Guía de Inicio Rápido - WhatsApp MCP

> **¿Qué es esto?** Un programa que conecta Claude con WhatsApp para enviar mensajes automáticamente.

## ⚡ Inicio en 3 pasos (5 minutos)

### 1️⃣ **Descargar y Configurar**
```bash
# Ejecuta esto como ADMINISTRADOR en PowerShell
cd C:\whatsapp-mcp-secure
.\scripts\setup.ps1 -All
```

### 2️⃣ **Iniciar el Servidor**
```bash
# Doble clic en este archivo:
scripts\start.bat
```
- Se abrirán 2 ventanas nuevas
- Una mostrará un **código QR**
- **Escanéalo con tu teléfono** (WhatsApp > Dispositivos Vinculados)

### 3️⃣ **Configurar Claude**
```bash
# Ejecuta esto una sola vez:
cd mcp-server
python configure_claude.py
```
- Luego **reinicia Claude Desktop**

## ✅ **¿Funcionó?**

En Claude, escribe:
```
Envía un WhatsApp a [nombre del contacto] diciendo "Hola desde Claude"
```

Si funciona: **¡Listo! 🎉**

Si no funciona: Ver [Solución de Problemas](#solución-de-problemas)

---

## 🔧 **¿Cómo funciona?**

```
Tu PC ← → WhatsApp Bridge ← → Claude ← → Tú
```

1. **WhatsApp Bridge**: Conecta con WhatsApp Web
2. **MCP Server**: Traduce comandos de Claude 
3. **Claude Desktop**: Tu interfaz para dar órdenes

---

## 📱 **Comandos útiles**

### Enviar mensajes
```
Envía WhatsApp a Juan: "Hola, ¿cómo estás?"
Envía a +549123456789: "Mensaje de prueba"
```

### Ver contactos
```
Muéstrame mis contactos de WhatsApp
Busca contactos que contengan "María"
```

### Verificar estado
```
¿Está conectado WhatsApp?
Muestra los últimos mensajes
```

---

## ❌ **Solución de Problemas** {#solución-de-problemas}

### El código QR no aparece
1. Cierra todo
2. Ejecuta `scripts\start.bat` de nuevo
3. Espera 30 segundos

### Claude no reconoce WhatsApp
1. Verifica que las 2 ventanas estén abiertas
2. Ejecuta: `python configure_claude.py`
3. Reinicia Claude Desktop
4. Espera 1 minuto antes de probar

### "Error de conexión"
1. Verifica tu internet
2. Revisa que WhatsApp Web funcione en el navegador
3. Reinicia el proceso completo

### Error de "Puerto ocupado"
1. Abre Administrador de Tareas
2. Busca procesos `go.exe` o `python.exe`
3. Termínalos y vuelve a intentar

---

## 🛡️ **Seguridad**

- ✅ Solo funciona en tu PC (no en internet)
- ✅ Datos cifrados localmente
- ✅ No almacenamos credenciales en la nube
- ⚠️ **Usar solo para automatización personal**

---

## 📞 **¿Necesitas ayuda?**

1. **Revisa los logs**: `logs/` carpeta
2. **Verifica el estado**: Ejecuta `test_mcp.py`
3. **Reporta problemas**: GitHub Issues

---

## 🎯 **Próximos pasos**

Una vez que funcione:
- Experimenta con diferentes comandos
- Lee el `README.md` completo para funciones avanzadas
- Configura backups automáticos
- Personaliza los scripts según tus necesidades
