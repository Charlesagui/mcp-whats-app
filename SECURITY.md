# 🔒 Configuración de Seguridad - WhatsApp MCP

## Variables de Entorno (.env)

El proyecto utiliza un archivo `.env` para configuraciones sensibles. **NUNCA** commitees el archivo `.env` real al repositorio.

### Configuración inicial:

1. **Copia el archivo ejemplo**:
   ```bash
   cp .env.example .env
   ```

2. **Ajusta las configuraciones** según tu entorno:
   ```bash
   # API Configuration
   WHATSAPP_API_HOST=localhost      # Cambiar si usas otro host
   WHATSAPP_API_PORT=8080          # Cambiar si usas otro puerto
   
   # Database Configuration  
   MESSAGES_DB_NAME=messages.db    # Cambiar nombre si quieres
   WHATSAPP_DB_NAME=whatsapp.db    # Cambiar nombre si quieres
   ```

### Variables disponibles:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `WHATSAPP_API_HOST` | Host del servidor REST | `localhost` |
| `WHATSAPP_API_PORT` | Puerto del servidor REST | `8080` |
| `WHATSAPP_API_BASE_URL` | URL completa de la API | `http://localhost:8080/api` |
| `MESSAGES_DB_NAME` | Nombre de la BD de mensajes | `messages.db` |
| `WHATSAPP_DB_NAME` | Nombre de la BD de WhatsApp | `whatsapp.db` |
| `REST_SERVER_PORT` | Puerto del servidor Go | `8080` |
| `DEBUG` | Modo debug | `false` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

## 🚨 Elementos de Seguridad Implementados:

✅ **Variables de entorno** para configuraciones sensibles
✅ **Archivo .env protegido** en .gitignore  
✅ **Rutas relativas** en lugar de hardcodeadas
✅ **Configuración por defecto** segura
✅ **Separación de secretos** del código

## 📁 Archivos protegidos por .gitignore:

- `.env` - Variables de entorno reales
- `whatsapp-bridge/store/` - Datos de WhatsApp y mensajes
- `*.db` - Todas las bases de datos
- `*.key`, `*.pem` - Claves y certificados
- `secrets/` - Carpeta de secretos

## 🔧 Para Producción:

1. **Cambia las configuraciones por defecto**
2. **Usa puertos no estándar**
3. **Configura firewall** apropiado
4. **Usa HTTPS** en lugar de HTTP
5. **Configura autenticación** si es necesario

## ⚠️ NUNCA hagas esto:

❌ Commitear archivos `.env` reales
❌ Hardcodear passwords o tokens
❌ Usar puertos por defecto en producción
❌ Exponer la API sin autenticación
❌ Commitear bases de datos con datos
