# WhatsApp MCP Server

This is a Model Context Protocol (MCP) server for WhatsApp that allows integration of WhatsApp with Claude Desktop.

## Features

- **Search and read** personal WhatsApp messages (including images, videos, documents, and audio messages)
- **Search contacts** and send messages to individuals or groups
- **Send multimedia files** including images, videos, documents, and audio messages
- **Direct connection** to your personal WhatsApp account via the WhatsApp multi-device web API
- **Local storage** of all messages in an SQLite database

## Architecture

The project consists of two main components:

1.  **Go WhatsApp Bridge** (`whatsapp-bridge/`): A Go application that connects to the WhatsApp web API, handles authentication via QR code, and stores message history in SQLite.

2.  **Python MCP Server** (`whatsapp-mcp-server/`): A Python server that implements the Model Context Protocol (MCP), providing standardized tools for Claude to interact with WhatsApp data.

## Requirements

- Go 1.24.1+
- Python 3.11+
- Claude Desktop app (or Cursor)
- UV (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- FFmpeg (optional) - Only needed for audio messages

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Charlesagui/mcp-whats-app.git
cd mcp-whats-app
```

### 2. Run the WhatsApp bridge
```bash
cd whatsapp-bridge
go run main.go
```

The first time you run this, you will need to scan a QR code with your WhatsApp mobile app to authenticate.

### 3. Connect to the MCP Server

Copy the following JSON configuration:

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "{{PATH_TO_UV}}",
      "args": [
        "--directory",
        "{{PATH_TO_SRC}}/mcp-whats-app/whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

For Claude Desktop, save this as `claude_desktop_config.json` in:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 4. Restart Claude Desktop

Open Claude Desktop, and you should see WhatsApp as an available integration.

## Windows Setup

If you are running on Windows, `go-sqlite3` requires CGO to be enabled:

### 1. Install a C compiler
We recommend using [MSYS2](https://www.msys2.org/) to install a C compiler for Windows.

### 2. Enable CGO and run the application
```bash
cd whatsapp-bridge
go env -w CGO_ENABLED=1
go run main.go
```

## Available Tools

Once connected, Claude can access the following tools:

- `search_contacts`: Search contacts by name or phone number
- `list_messages`: Retrieve messages with optional filters and context
- `list_chats`: List available chats with metadata
- `get_chat`: Get information about a specific chat
- `send_message`: Send a WhatsApp message to a specific number or group JID
- `send_file`: Send a file (image, video, raw audio, document)
- `send_audio_message`: Send an audio file as a WhatsApp voice message
- `download_media`: Download media from a WhatsApp message

## Data Storage

- All message history is stored in an SQLite database within the `whatsapp-bridge/store/` directory
- The database maintains tables for chats and messages
- Messages are indexed for efficient search and retrieval

## Troubleshooting

- **QR code not displaying**: Restart the authentication script. If it persists, check if your terminal supports displaying QR codes.
- **WhatsApp already connected**: If your session is already active, the Go bridge will reconnect automatically without showing a QR code.
- **Device limit reached**: WhatsApp limits the number of linked devices. You will need to remove an existing device from WhatsApp on your phone.
- **Messages not loading**: After initial authentication, it may take several minutes for your message history to load.

## License

MIT License
