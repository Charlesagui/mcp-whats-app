# WhatsApp MCP Secure - Local Environment

A secure implementation of the Model Context Protocol (MCP) for WhatsApp, designed for local execution. This tool provides a controlled environment for automating WhatsApp interactions with a strong emphasis on data security and privacy.

```
Your PC ← → WhatsApp Bridge ← → Claude ← → You
```

## ✨ Key Features

- 💬 **Automated Messaging**: Send and receive WhatsApp messages through Claude
- 🔒 **Security First**:
  - Database encryption with SQLite + SQLCipher
  - Secure token authentication
  - Process isolation
  - Secure credential management
- 📊 **Comprehensive Logging**: Full audit trail of all activities
- 🔄 **Easy Integration**: Simple setup process with Claude Desktop

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Windows 10/11 or Linux
- Go 1.21+
- Python 3.10+
- FFmpeg (optional, for audio messages)

### 1. Initial Setup
```bash
# Clone the repository
git clone https://github.com/Charlesagui/mcp-whats-app.git
cd whatsapp-mcp-secure

# Run setup as Administrator
.\scripts\setup.ps1 -All
```

### 2. Start the Server
```bash
# Double-click this file or run in terminal:
scripts\start.bat
```
- Two new windows will open
- One will show a **QR code**
- **Scan it with your phone** (WhatsApp > Linked Devices)

### 3. Configure Claude
```bash
# Run this just once:
python mcp-server\configure_claude.py
```
- Then **restart Claude Desktop**
- Wait 30 seconds before testing

### 4. Test It!
In Claude, try:
```
Send a WhatsApp to [contact name] saying "Hello from Claude"
```

## 🛠️ Usage Examples

### Send Messages
```
"Send WhatsApp to John: 'Meeting at 3pm'"
"Send to +549123456789: 'Running late, be there in 10'"
```

### Manage Contacts
```
"Show my WhatsApp contacts"
"Search contacts containing 'Maria'"
```

### Check Status
```
"Is WhatsApp connected?"
"Show recent messages"
```

## ⚠️ Common Issues & Solutions

### QR Code Doesn't Appear
1. Close all WhatsApp Web sessions in your browser
2. Run `scripts\start.bat` again
3. Wait 30 seconds for QR code to appear

### Claude Doesn't Recognize WhatsApp
1. Ensure both server windows are running
2. Run: `python mcp-server\configure_claude.py`
3. Restart Claude Desktop
4. Wait 1 minute before testing

### Port 8081 in Use
```bash
# Windows
netstat -ano | findstr :8081
taskkill /PID [process_id] /F
```

## 🔒 Security & Privacy

⚠️ **Important Notice**: This software is not affiliated with WhatsApp. Use at your own risk and be aware of WhatsApp's Terms of Service.

- For personal and educational use only
- Do not send spam or malicious content
- Keep software updated
- Monitor logs regularly

## 🤝 Support

Found a bug or have a question? Please open an issue in the repository.

## ☕ Support the Project

If you find this project useful, consider supporting its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/aguiar843y)

## 📄 License

MIT License - See the [LICENSE](LICENSE) file for details.
