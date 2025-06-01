# WhatsApp MCP Secure - Entorno Local

Implementación del Model Context Protocol (MCP) para WhatsApp, diseñada para ejecución local. Proporciona un entorno seguro y controlado para la automatización de interacciones con WhatsApp, con énfasis en seguridad y privacidad de los datos.

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

## 🚀 Inicio Rápido

> 📖 **¿Primera vez?** Sigue la [Guía de Inicio Rápido](QUICKSTART.md) para una configuración paso a paso en 5 minutos.

### 🔄 Verificar Instalación

```bash
# Verificar que todo funciona correctamente
python test_mcp.py

# Ver estado actual
python -c "import requests; print(requests.get('http://localhost:8081/health').json())"
```

### Método Recomendado (Windows)
```bash
# 1. Clonar el repositorio
git clone https://github.com/Charlesagui/mcp-whats-app.git
cd whatsapp-mcp-secure

# 2. Configurar e iniciar (ejecutar como administrador)
scripts\start.bat
```

### Método Manual (opcional)
Si necesitas más control, puedes iniciar los componentes manualmente:

```bash
# 1. Configuración inicial
.\scripts\setup.ps1

# 2. En una terminal, iniciar el bridge de WhatsApp
cd whatsapp-bridge
go run main.go

# 3. En otra terminal, iniciar el servidor MCP
cd mcp-server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 📖 Ejemplos de Uso

Una vez configurado, puedes usar estos comandos en Claude:

```
# Enviar mensajes
"Envía un WhatsApp a María diciendo 'Hola desde Claude'"
"Manda mensaje a +549123456789: 'Prueba de automatización'"

# Gestionar contactos  
"Muestra mis contactos de WhatsApp"
"Busca contactos con 'Juan'"

# Verificar estado
"¿Está conectado WhatsApp?"
"Muestra los últimos 5 mensajes"
```

## ⚙️ Configuración

1. Copia `.env.example` a `.env`
2. Configura tus tokens y credenciales
3. Ejecuta el script de configuración inicial

## 🔧 Solución de Problemas Comunes

#### ❌ "Puerto 8081 ya está en uso"
```bash
# Windows
netstat -ano | findstr :8081
taskkill /PID [número_de_proceso] /F

# Luego reiniciar con start.bat
```

#### ❌ "No se puede conectar a WhatsApp"
1. Verifica que WhatsApp Web funcione en tu navegador
2. Cierra todas las sesiones de WhatsApp Web
3. Ejecuta `scripts\start.bat` nuevamente
4. Escanea el código QR cuando aparezca

#### ❌ "Claude no reconoce las herramientas de WhatsApp"
1. Ejecuta `python scripts\configure_claude.py`
2. Reinicia Claude Desktop completamente
3. Espera 30 segundos antes de usar comandos

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
