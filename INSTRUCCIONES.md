# WhatsApp MCP - Guía de Uso

## Archivos .bat creados:

### 1. `instalar-dependencias.bat` 
- **Ejecutar PRIMERO** para instalar todas las dependencias
- Instala dependencias Go y Python
- Verifica que todo esté configurado correctamente

### 2. `iniciar-whatsapp-bridge.bat`
- **Ejecutar cada vez** que quieras usar WhatsApp con Claude
- Inicia el servidor Go que se conecta a WhatsApp
- La primera vez te pedirá escanear un código QR
- **MANTENER ABIERTO** mientras uses Claude

### 3. `verificar-configuracion.bat`
- Verifica que todo esté funcionando
- Útil para troubleshooting

## Pasos para usar:

### Primera configuración:
1. ✅ **Ejecutar**: `instalar-dependencias.bat`
2. ✅ **Configurar**: Claude Desktop config (ya hecho)
3. ✅ **Ejecutar**: `iniciar-whatsapp-bridge.bat`
4. ✅ **Escanear**: Código QR con WhatsApp móvil
5. ✅ **Reiniciar**: Claude Desktop

### Uso diario:
1. **Ejecutar**: `iniciar-whatsapp-bridge.bat` (mantener abierto)
2. **Abrir**: Claude Desktop
3. **Usar**: WhatsApp tools en Claude

## Herramientas disponibles en Claude:

- `search_contacts` - Buscar contactos
- `list_messages` - Ver mensajes
- `list_chats` - Ver chats
- `send_message` - Enviar mensajes
- `send_file` - Enviar archivos
- `download_media` - Descargar multimedia

## Troubleshooting:

Si algo no funciona:
1. Ejecutar `verificar-configuracion.bat`
2. Verificar que el bridge esté ejecutándose
3. Reiniciar Claude Desktop
4. Verificar configuración en `%APPDATA%\Claude\claude_desktop_config.json`
