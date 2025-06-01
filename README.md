# WhatsApp MCP Secure - Versión Local Mejorada

Una implementación segura del Model Context Protocol (MCP) para WhatsApp con mejoras de seguridad y privacidad.

## 🔒 Características de Seguridad

- ✅ Cifrado de base de datos con SQLite + SQLCipher
- ✅ Autenticación con tokens seguros
- ✅ Logging y auditoría completos
- ✅ Aislamiento de procesos
- ✅ Gestión segura de credenciales
- ✅ Backups automáticos cifrados

## 📋 Requisitos

- Go 1.21+
- Python 3.10+
- SQLCipher
- FFmpeg (opcional, para mensajes de audio)
- Windows 10/11 o Linux

## 🚀 Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/Charlesagui/mcp-whats-app.git
cd whatsapp-mcp-secure

# 2. Configurar entorno
.\scripts\setup.ps1

# 3. Ejecutar el bridge de WhatsApp
cd whatsapp-bridge
go run main.go

# 4. En otra terminal, ejecutar el servidor MCP
cd mcp-server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## ⚙️ Configuración

1. Copia `.env.example` a `.env`
2. Configura tus tokens y credenciales
3. Ejecuta el script de configuración inicial

## 🛡️ Consideraciones de Seguridad

⚠️ **IMPORTANTE**: Este software no está afiliado con WhatsApp. Su uso puede violar los Términos de Servicio de WhatsApp y resultar en el bloqueo de tu cuenta.

- Solo para uso personal y educativo
- No enviar spam o contenido malicioso
- Mantener actualizadas las dependencias
- Revisar logs regularmente

## 📞 Soporte

Para reportes de seguridad o bugs, abrir un issue en el repositorio.

## 📄 Licencia

MIT License - Ver archivo LICENSE para detalles.
