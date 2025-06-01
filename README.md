# WhatsApp MCP Secure - Local Environment

Implementation of the Model Context Protocol (MCP) for WhatsApp, designed for local execution. Provides a secure and controlled environment for automating WhatsApp interactions, with emphasis on data security and privacy.

## 🔒 Security Features

- ✅ Database encryption with SQLite + SQLCipher
- ✅ Secure token authentication
- ✅ Comprehensive logging and auditing
- ✅ Process isolation
- ✅ Secure credential management
- ✅ Automatic encrypted backups

## 📋 Requirements

- Go 1.21+
- Python 3.10+
- SQLCipher
- FFmpeg (optional, for audio messages)
- Windows 10/11 or Linux

## 🚀 Quick Start

> 📖 **First time?** Follow the [Quick Start Guide](QUICKSTART.md) for a 5-minute step-by-step setup.

### 🔄 Verify Installation

```bash
# Verify everything works correctly
python test_mcp.py

# Check current status
python -c "import requests; print(requests.get('http://localhost:8081/health').json())"
```

### Recommended Method (Windows)
```bash
# 1. Clone the repository
git clone https://github.com/Charlesagui/mcp-whats-app.git
cd whatsapp-mcp-secure

# 2. Configure and start (run as administrator)
scripts\start.bat
```

### Manual Method (optional)
If you need more control, you can start components manually:

```bash
# 1. Initial setup
.\scripts\setup.ps1

# 2. In one terminal, start the WhatsApp bridge
cd whatsapp-bridge
go run main.go

# 3. In another terminal, start the MCP server
cd mcp-server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 📖 Usage Examples

Once set up, you can use these commands in Claude:

```
# Send messages
"Send a WhatsApp to Maria saying 'Hello from Claude'"
"Send message to +549123456789: 'Automation test'"

# Manage contacts  
"Show my WhatsApp contacts"
"Search contacts with 'John'"

# Check status
"Is WhatsApp connected?"
"Show last 5 messages"
```

## ⚙️ Configuration

1. Copy `.env.example` to `.env`
2. Configure your tokens and credentials
3. Run the initial setup script

## 🔧 Common Issues

#### ❌ "Port 8081 is already in use"
```bash
# Windows
netstat -ano | findstr :8081
taskkill /PID [process_id] /F

# Then restart with start.bat
```

#### ❌ "Cannot connect to WhatsApp"
1. Verify WhatsApp Web works in your browser
2. Close all WhatsApp Web sessions
3. Run `scripts\start.bat` again
4. Scan the QR code when it appears

#### ❌ "Claude doesn't recognize WhatsApp tools"
1. Run `python scripts\configure_claude.py`
2. Completely restart Claude Desktop
3. Wait 30 seconds before using commands

## 🛡️ Security Considerations

⚠️ **IMPORTANT**: This software is not affiliated with WhatsApp. Its use may violate WhatsApp's Terms of Service and could result in your account being banned.

- For personal and educational use only
- Do not send spam or malicious content
- Keep dependencies updated
- Regularly check logs

## 📞 Support

For security reports or bugs, please open an issue in the repository.

## ☕ Support

If you find this project useful and would like to support my work, feel free to buy me a coffee! Your support helps me continue improving this project and creating quality content.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/aguiar843y)

## 📄 License

MIT License - See the LICENSE file for details.
