# 🚀 Quick Start Guide - WhatsApp MCP

> **What is this?** A program that connects Claude with WhatsApp to send messages automatically.

## ⚡ Get Started in 3 Steps (5 minutes)

### 1️⃣ **Download and Configure**
```bash
# Run this as ADMINISTRATOR in PowerShell
cd C:\whatsapp-mcp-secure
.\scripts\setup.ps1 -All
```

### 2️⃣ **Start the Server**
```bash
# Double-click this file:
scripts\start.bat
```
- Two new windows will open
- One will show a **QR code**
- **Scan it with your phone** (WhatsApp > Linked Devices)

### 3️⃣ **Configure Claude**
```bash
# Run this just once:
cd mcp-server
python configure_claude.py
```
- Then **restart Claude Desktop**

## ✅ **Did it work?**

In Claude, type:
```
Send a WhatsApp to [contact name] saying "Hello from Claude"
```

If it works: **You're all set! 🎉**

If not: See [Troubleshooting](#troubleshooting)

---

## 🔧 **How does it work?**

```
Your PC ← → WhatsApp Bridge ← → Claude ← → You
```

1. **WhatsApp Bridge**: Connects to WhatsApp Web
2. **MCP Server**: Translates Claude's commands 
3. **Claude Desktop**: Your interface to give commands

---

## 📱 **Useful Commands**

### Send messages
```
Send WhatsApp to John: "Hi, how are you?"
Send to +549123456789: "Test message"
```

### View contacts
```
Show my WhatsApp contacts
Search contacts containing "Maria"
```

### Check status
```
Is WhatsApp connected?
Show recent messages
```

---

## ❌ **Troubleshooting** {#troubleshooting}

### QR code doesn't appear
1. Close everything
2. Run `scripts\start.bat` again
3. Wait 30 seconds

### Claude doesn't recognize WhatsApp
1. Make sure both windows are open
2. Run: `python configure_claude.py`
3. Restart Claude Desktop
4. Wait 1 minute before testing

### "Connection error"
1. Check your internet connection
2. Make sure WhatsApp Web works in your browser
3. Restart the whole process

### "Port in use" error
1. Open Task Manager
2. Look for `go.exe` or `python.exe` processes
3. End them and try again

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
