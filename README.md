# WhatsApp MCP Server

Este es un servidor Model Context Protocol (MCP) para WhatsApp que permite integrar WhatsApp con Claude Desktop.

## Características

- **Búsqueda y lectura de mensajes** personales de WhatsApp (incluyendo imágenes, videos, documentos y mensajes de audio)
- **Búsqueda de contactos** y envío de mensajes a individuos o grupos
- **Envío de archivos multimedia** incluyendo imágenes, videos, documentos y mensajes de audio
- **Conexión directa** a tu cuenta personal de WhatsApp vía la API web multidevice de WhatsApp
- **Almacenamiento local** de todos los mensajes en una base de datos SQLite

## Arquitectura

El proyecto consta de dos componentes principales:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): Aplicación Go que se conecta a la API web de WhatsApp, maneja la autenticación via código QR, y almacena el historial de mensajes en SQLite.

2. **Python MCP Server** (`whatsapp-mcp-server/`): Servidor Python que implementa el Protocolo de Contexto de Modelo (MCP), proporcionando herramientas estandarizadas para que Claude interactúe con los datos de WhatsApp.

## Requisitos

- Go 1.24.1+
- Python 3.11+
- Claude Desktop app (o Cursor)
- UV (gestor de paquetes Python): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- FFmpeg (opcional) - Solo necesario para mensajes de audio

## Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tuusuario/mi-whatsapp-mcp.git
cd mi-whatsapp-mcp
```

### 2. Ejecutar el bridge de WhatsApp
```bash
cd whatsapp-bridge
go run main.go
```

La primera vez deberás escanear un código QR con tu aplicación móvil de WhatsApp para autenticarte.

### 3. Conectar al servidor MCP

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

Para Claude Desktop, guarda esto como `claude_desktop_config.json` en:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 4. Reiniciar Claude Desktop

Abre Claude Desktop y deberías ver WhatsApp como una integración disponible.

## Configuración para Windows

Si estás ejecutando en Windows, `go-sqlite3` requiere CGO habilitado:

### 1. Instalar un compilador C
Recomendamos usar [MSYS2](https://www.msys2.org/) para instalar un compilador C para Windows.

### 2. Habilitar CGO y ejecutar la aplicación
```bash
cd whatsapp-bridge
go env -w CGO_ENABLED=1
go run main.go
```

## Herramientas Disponibles

Una vez conectado, Claude puede acceder a las siguientes herramientas:

- `search_contacts`: Buscar contactos por nombre o número de teléfono
- `list_messages`: Recuperar mensajes con filtros opcionales y contexto
- `list_chats`: Listar chats disponibles con metadatos
- `get_chat`: Obtener información sobre un chat específico
- `send_message`: Enviar un mensaje de WhatsApp a un número específico o JID de grupo
- `send_file`: Enviar un archivo (imagen, video, audio crudo, documento)
- `send_audio_message`: Enviar un archivo de audio como mensaje de voz de WhatsApp
- `download_media`: Descargar multimedia de un mensaje de WhatsApp

## Almacenamiento de Datos

- Todo el historial de mensajes se almacena en una base de datos SQLite dentro del directorio `whatsapp-bridge/store/`
- La base de datos mantiene tablas para chats y mensajes
- Los mensajes están indexados para búsqueda y recuperación eficiente

## Solución de Problemas

- **Código QR no se muestra**: Reinicia el script de autenticación. Si persiste, verifica que tu terminal soporte mostrar códigos QR.
- **WhatsApp ya conectado**: Si tu sesión ya está activa, el bridge Go se reconectará automáticamente sin mostrar un código QR.
- **Límite de dispositivos alcanzado**: WhatsApp limita el número de dispositivos vinculados. Deberás eliminar un dispositivo existente desde WhatsApp en tu teléfono.
- **Mensajes no cargan**: Después de la autenticación inicial, puede tomar varios minutos para que tu historial de mensajes cargue.

## Licencia

MIT License
