# WhatsApp MCP Server

Este es un servidor Model Context Protocol (MCP) para WhatsApp que permite integrar WhatsApp con Claude Desktop.

## 📋 Índice
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación y Configuración](#instalación-y-configuración)
- [Guía de Uso](#guía-de-uso)
- [Herramientas Disponibles](#herramientas-disponibles)
- [Almacenamiento de Datos](#almacenamiento-de-datos)
- [Seguridad](#seguridad)
- [Solución de Problemas](#solución-de-problemas)
- [Licencia](#licencia)

## 🚀 Características

- **Búsqueda y lectura de mensajes** personales de WhatsApp (incluyendo imágenes, videos, documentos y mensajes de audio)
- **Búsqueda de contactos** y envío de mensajes a individuos o grupos
- **Envío de archivos multimedia** incluyendo imágenes, videos, documentos y mensajes de audio
- **Conexión directa** a tu cuenta personal de WhatsApp vía la API web multidevice de WhatsApp
- **Almacenamiento local** de todos los mensajes en una base de datos SQLite

## 🏗️ Arquitectura

El proyecto consta de dos componentes principales:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): Aplicación Go que se conecta a la API web de WhatsApp, maneja la autenticación via código QR, y almacena el historial de mensajes en SQLite.

2. **Python MCP Server** (`whatsapp-mcp-server/`): Servidor Python que implementa el Protocolo de Contexto de Modelo (MCP), proporcionando herramientas estandarizadas para que Claude interactúe con los datos de WhatsApp.

## 📋 Requisitos

- Go 1.24.1+
- Python 3.11+
- Claude Desktop app (o Cursor)
- UV (gestor de paquetes Python): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- FFmpeg (opcional) - Solo necesario para mensajes de audio

## 🔧 Instalación y Configuración

### Scripts de Instalación

El proyecto incluye tres archivos batch para facilitar la instalación y uso:

1. **`instalar-dependencias.bat`**
   - **Ejecutar PRIMERO** para instalar todas las dependencias
   - Instala dependencias Go y Python
   - Crea el archivo `.env` a partir de `.env.example` si no existe

2. **`iniciar-whatsapp-bridge.bat`**
   - **Ejecutar cada vez** que quieras usar WhatsApp con Claude
   - Inicia el servidor Go que se conecta a WhatsApp
   - La primera vez te pedirá escanear un código QR
   - **MANTENER ABIERTO** mientras uses Claude

3. **`verificar-configuracion.bat`**
   - Verifica que todo esté funcionando correctamente
   - Útil para solucionar problemas

### Instalación Manual

Si prefieres la instalación manual, sigue estos pasos:

1. **Clonar el repositorio**
```bash
git clone https://github.com/tuusuario/mi-whatsapp-mcp.git
cd mi-whatsapp-mcp
```

2. **Configurar el entorno**
```bash
cp .env.example .env
# Edita .env si necesitas personalizar la configuración
```

3. **Instalar dependencias Go**
```bash
cd whatsapp-bridge
go mod tidy
```

4. **Instalar dependencias Python**
```bash
cd ../whatsapp-mcp-server
uv sync
```

### Configuración para Windows

Si estás ejecutando en Windows, `go-sqlite3` requiere CGO habilitado:

1. **Instalar un compilador C**
   - Recomendamos usar [MSYS2](https://www.msys2.org/) para instalar un compilador C para Windows.

2. **Habilitar CGO y ejecutar la aplicación**
```bash
cd whatsapp-bridge
go env -w CGO_ENABLED=1
go run main.go
```

### Configuración de Claude Desktop

Para conectar Claude Desktop con el servidor MCP:

1. **Crear archivo de configuración**

Copia la siguiente configuración JSON:

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "{{PATH_TO_UV}}",
      "args": [
        "--directory",
        "{{PATH_TO_SRC}}/mi-whatsapp-mcp/whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

2. **Guardar la configuración** en la ubicación adecuada:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

3. **Reiniciar Claude Desktop**

## 📝 Guía de Uso

### Primera configuración:
1. ✅ **Ejecutar**: `instalar-dependencias.bat`
2. ✅ **Configurar**: Claude Desktop config (según las instrucciones anteriores)
3. ✅ **Ejecutar**: `iniciar-whatsapp-bridge.bat`
4. ✅ **Escanear**: Código QR con WhatsApp móvil
5. ✅ **Reiniciar**: Claude Desktop

### Uso diario:
1. **Ejecutar**: `iniciar-whatsapp-bridge.bat` (mantener abierto)
2. **Abrir**: Claude Desktop
3. **Usar**: WhatsApp tools en Claude

## 🛠️ Herramientas Disponibles

Una vez conectado, Claude puede acceder a las siguientes herramientas:

- `search_contacts`: Buscar contactos por nombre o número de teléfono
- `list_messages`: Recuperar mensajes con filtros opcionales y contexto
- `get_last_interaction`: Obtener el último mensaje con un contacto específico
- `get_message_context`: Obtener contexto alrededor de un mensaje específico
- `send_message`: Enviar un mensaje de WhatsApp a un número específico o JID de grupo
- `send_file`: Enviar un archivo (imagen, video, audio crudo, documento)
- `send_audio_message`: Enviar un archivo de audio como mensaje de voz de WhatsApp
- `download_media`: Descargar multimedia de un mensaje de WhatsApp

## 💾 Almacenamiento de Datos

- Todo el historial de mensajes se almacena en una base de datos SQLite dentro del directorio `whatsapp-bridge/store/`
- La base de datos mantiene tablas para chats y mensajes
- Los mensajes están indexados para búsqueda y recuperación eficiente
- Todos los datos se almacenan localmente en tu equipo, no en servidores externos

## 🔒 Seguridad

El proyecto implementa varias medidas de seguridad:

- **Variables de entorno** para configuraciones sensibles
- **Archivo .env protegido** en .gitignore
- **Rutas relativas** en lugar de hardcodeadas
- **Configuración por defecto** segura
- **Separación de secretos** del código

Para más detalles sobre seguridad, consulta el archivo [SECURITY.md](./SECURITY.md).

## ❓ Solución de Problemas

Si encuentras problemas al usar WhatsApp MCP:

1. **Código QR no se muestra**: 
   - Reinicia el script de autenticación
   - Verifica que tu terminal soporte mostrar códigos QR

2. **WhatsApp ya conectado**: 
   - Si tu sesión ya está activa, el bridge Go se reconectará automáticamente sin mostrar un código QR

3. **Límite de dispositivos alcanzado**: 
   - WhatsApp limita el número de dispositivos vinculados
   - Deberás eliminar un dispositivo existente desde WhatsApp en tu teléfono

4. **Mensajes no cargan**: 
   - Después de la autenticación inicial, puede tomar varios minutos para que tu historial de mensajes cargue

5. **Problemas de conexión**:
   - Ejecuta `verificar-configuracion.bat`
   - Verifica que el bridge esté ejecutándose
   - Reinicia Claude Desktop
   - Verifica configuración en `%APPDATA%\Claude\claude_desktop_config.json`

## 📄 Licencia

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
