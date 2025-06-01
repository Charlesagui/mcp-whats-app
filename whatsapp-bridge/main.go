package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/joho/godotenv"
	"github.com/mdp/qrterminal"
	_ "github.com/mattn/go-sqlite3"
	"github.com/sirupsen/logrus"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
)

type WhatsAppBridge struct {
	client   *whatsmeow.Client
	logger   *logrus.Logger
	config   *Config
	messages []Message
	contacts []Contact
	mu       sync.RWMutex
}

type Config struct {
	AdminToken       string `json:"admin_token"`
	MCPPort         string `json:"mcp_port"`
	MCPHost         string `json:"mcp_host"`
	DBEncryptionKey string `json:"db_encryption_key"`
	DBPath          string `json:"db_path"`
	BridgePort      string `json:"bridge_port"`
	DeviceName      string `json:"device_name"`
	WhatsAppTimeout int    `json:"whatsapp_timeout"`
	LogLevel        string `json:"log_level"`
	LogPath         string `json:"log_path"`
}

type Message struct {
	ID        string    `json:"id"`
	ChatJID   string    `json:"chat_jid"`
	SenderJID string    `json:"sender_jid"`
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
	MessageType string  `json:"message_type"`
	MediaPath   string  `json:"media_path,omitempty"`
}

type Contact struct {
	JID  string `json:"jid"`
	Name string `json:"name"`
}

type SendMessageRequest struct {
	ChatJID string `json:"chat_jid"`
	Content string `json:"content"`
}

type APIResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

func main() {
	bridge := &WhatsAppBridge{
		logger:   logrus.New(),
		messages: make([]Message, 0),
		contacts: make([]Contact, 0),
	}

	// Load configuration
	if err := bridge.loadConfig(); err != nil {
		log.Fatal("Error cargando configuración:", err)
	}

	// Configurar logging
	bridge.setupLogging()

	// Initialize REAL WhatsApp
	if err := bridge.initWhatsApp(); err != nil {
		bridge.logger.Fatal("Error inicializando WhatsApp:", err)
	}

	// Configure HTTP routes
	router := bridge.setupRoutes()

	// Start HTTP server
	server := &http.Server{
		Addr:    ":" + bridge.config.BridgePort,
		Handler: router,
	}

	go func() {
		bridge.logger.Info("🚀 Iniciando WhatsApp Bridge REAL en puerto ", bridge.config.BridgePort)
		bridge.logger.Info("📱 WhatsApp conectado - Mensajes reales disponibles")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			bridge.logger.Fatal("Error iniciando servidor HTTP:", err)
		}
	}()

	// Wait for shutdown signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	bridge.logger.Info("Cerrando WhatsApp Bridge...")

	// Close WhatsApp client
	if bridge.client != nil {
		bridge.client.Disconnect()
	}

	// Close HTTP server
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		bridge.logger.Error("Error cerrando servidor HTTP:", err)
	}

	bridge.logger.Info("WhatsApp Bridge cerrado correctamente")
}

func (b *WhatsAppBridge) loadConfig() error {
	// Load .env file
	if err := godotenv.Load("../.env"); err != nil {
		b.logger.Warn("No se pudo cargar archivo .env, usando variables de entorno")
	}

	b.config = &Config{
		AdminToken:       getEnv("ADMIN_TOKEN", "default_admin_token"),
		MCPPort:         getEnv("MCP_PORT", "8080"),
		MCPHost:         getEnv("MCP_HOST", "127.0.0.1"),
		DBEncryptionKey: getEnv("DB_ENCRYPTION_KEY", "default_encryption_key"),
		DBPath:          getEnv("DB_PATH", "../data/whatsapp_secure.db"),
		BridgePort:      getEnv("BRIDGE_PORT", "8081"),
		DeviceName:      getEnv("DEVICE_NAME", "WhatsApp-MCP-Secure"),
		WhatsAppTimeout: getEnvInt("WHATSAPP_TIMEOUT", 30),
		LogLevel:        getEnv("LOG_LEVEL", "INFO"),
		LogPath:         getEnv("LOG_PATH", "../logs"),
	}

	return nil
}

func (b *WhatsAppBridge) setupLogging() {
	level, err := logrus.ParseLevel(b.config.LogLevel)
	if err != nil {
		level = logrus.InfoLevel
	}
	b.logger.SetLevel(level)

	// Create logs directory if it doesn't exist
	if err := os.MkdirAll(b.config.LogPath, 0750); err != nil {
		b.logger.Error("Error creando directorio de logs:", err)
	}

	// Configure log format
	b.logger.SetFormatter(&logrus.JSONFormatter{
		TimestampFormat: time.RFC3339,
	})
}

func (b *WhatsAppBridge) initWhatsApp() error {
	// Create authentication directory
	authDir := "../auth"
	if err := os.MkdirAll(authDir, 0700); err != nil {
		return fmt.Errorf("error creando directorio de auth: %v", err)
	}

	// Configure WhatsApp store with persistent SQLite
	dbLog := waLog.Stdout("Database", "INFO", true)
	container, err := sqlstore.New(context.Background(), "sqlite3", "file:"+authDir+"/whatsapp.db?_foreign_keys=on", dbLog)
	if err != nil {
		return fmt.Errorf("error creando container de WhatsApp: %v", err)
	}

	// Get device store
	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		return fmt.Errorf("error obteniendo device store: %v", err)
	}

	// Configure WhatsApp logging
	clientLog := waLog.Stdout("Client", "INFO", true)

	// Create client
	b.client = whatsmeow.NewClient(deviceStore, clientLog)

	// Configure event handlers
	b.client.AddEventHandler(b.handleMessage)
	b.client.AddEventHandler(b.handleReceipt)
	b.client.AddEventHandler(b.handleConnected)

	// Connect
	if b.client.Store.ID == nil {
		// First time - show QR
		b.logger.Info("🔄 Primera vez conectando - generando código QR...")
		qrChan, _ := b.client.GetQRChannel(context.Background())
		err = b.client.Connect()
		if err != nil {
			return fmt.Errorf("error conectando a WhatsApp: %v", err)
		}

		fmt.Println("\n" + strings.Repeat("=", 60))
		fmt.Println("📱 ESCANEA ESTE CÓDIGO QR CON TU WHATSAPP")
		fmt.Println(strings.Repeat("=", 60))
		for evt := range qrChan {
			if evt.Event == "code" {
				// Show QR code in terminal
				fmt.Println("\n🔳 Código QR:")
				qrterminal.Generate(evt.Code, qrterminal.L, os.Stdout)
				fmt.Println("\n👆 Escanea este código QR con WhatsApp en tu teléfono")
				fmt.Println("📱 Ve a WhatsApp > Dispositivos Vinculados > Vincular Dispositivo")
				fmt.Println(strings.Repeat("=", 60))
			} else {
				b.logger.Info("Estado QR:", evt.Event)
				if evt.Event == "success" {
					b.logger.Info("🎉 ¡WhatsApp conectado exitosamente!")
					break
				}
			}
		}
	} else {
		// Reconnect
		err = b.client.Connect()
		if err != nil {
			return fmt.Errorf("error reconectando a WhatsApp: %v", err)
		}
		b.logger.Info("🔄 Reconectado a WhatsApp existente")
	}

	b.logger.Info("✅ WhatsApp conectado correctamente")
	
	// Start contact synchronization
	go b.syncContacts()
	
	return nil
}

// In-memory storage functions
func (b *WhatsAppBridge) saveMessage(v *events.Message) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	// Extract message content
	var content string
	var messageType string = "text"
	
	if v.Message.GetConversation() != "" {
		content = v.Message.GetConversation()
	} else if v.Message.GetExtendedTextMessage() != nil {
		content = v.Message.GetExtendedTextMessage().GetText()
	} else if v.Message.GetImageMessage() != nil {
		content = "[Imagen]"
		messageType = "image"
	} else if v.Message.GetVideoMessage() != nil {
		content = "[Video]"
		messageType = "video"
	} else if v.Message.GetAudioMessage() != nil {
		content = "[Audio]"
		messageType = "audio"
	} else if v.Message.GetDocumentMessage() != nil {
		content = "[Documento]"
		messageType = "document"
	} else {
		content = "[Mensaje no soportado]"
		messageType = "unknown"
	}

	// Save to memory
	msg := Message{
		ID:          v.Info.ID,
		ChatJID:     v.Info.Chat.String(),
		SenderJID:   v.Info.Sender.String(),
		Content:     content,
		Timestamp:   v.Info.Timestamp,
		MessageType: messageType,
	}

	b.messages = append(b.messages, msg)
	
	b.logger.Info(fmt.Sprintf("💬 Mensaje recibido: %s de %s", content[:min(50, len(content))], v.Info.Sender.String()))
	return nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}


// Event handler for successful connection
func (b *WhatsAppBridge) handleConnected(evt interface{}) {
	b.logger.Info("🔗 WhatsApp conectado - sincronizando contactos...")
	go b.syncContacts()
}

// Synchronize contacts from WhatsApp
func (b *WhatsAppBridge) syncContacts() {
	if b.client == nil || !b.client.IsConnected() {
		b.logger.Warn("Cliente no conectado para sincronizar contactos")
		return
	}

	// Wait a moment for the connection to stabilize
	time.Sleep(2 * time.Second)

	// Get contacts using whatsmeow
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Try to get contacts from store
	contacts, err := b.client.Store.Contacts.GetAllContacts(ctx)
	if err != nil {
		b.logger.Error("Error getting contacts from store:", err)
		// Try alternative method - get from recent chats
		b.syncContactsFromChats()
		return
	}

	b.mu.Lock()
	defer b.mu.Unlock()

	// Limpiar contactos existentes
	b.contacts = make([]Contact, 0)

	// Convert and save contacts with user name priority
	for jid, contact := range contacts {
		var contactName string
		if contact.Found {
			// Name priority:
			// 1. FullName (user-configured full name)
			// 2. FirstName (user-configured first name)
			// 3. PushName (person's profile name)
			// 4. BusinessName (for businesses)
			
			if contact.FullName != "" {
				contactName = contact.FullName
			} else if contact.FirstName != "" {
				contactName = contact.FirstName
			} else if contact.PushName != "" {
				contactName = contact.PushName
			} else if contact.BusinessName != "" {
				contactName = contact.BusinessName
			} else {
				continue // Skip si no hay nombre
			}
			
			b.contacts = append(b.contacts, Contact{
				JID:  jid.String(),
				Name: contactName,
			})
		}
	}

	b.logger.Info(fmt.Sprintf("📞 Sincronizados %d contactos", len(b.contacts)))
}

// Alternative method: synchronize contacts from recent chats
func (b *WhatsAppBridge) syncContactsFromChats() {
	if b.client == nil || !b.client.IsConnected() {
		return
	}

	// Get recent conversations - use correct whatsmeow method
	// For now, use an alternative method based on stored messages
	b.syncContactsFromMessages()
}



// Alternative method: synchronize contacts from stored messages
func (b *WhatsAppBridge) syncContactsFromMessages() {
	b.mu.Lock()
	defer b.mu.Unlock()

	// Limpiar contactos existentes
	b.contacts = make([]Contact, 0)
	
	// Create a map to avoid duplicates
	contactMap := make(map[string]string)

	// Process messages to extract unique contacts
	for _, msg := range b.messages {
		if msg.SenderJID != "self" && msg.SenderJID != "" {
			// Extract phone number from JID
			if _, exists := contactMap[msg.SenderJID]; !exists {
				// Use number as temporary name (can be improved later)
				contactMap[msg.SenderJID] = msg.SenderJID
			}
		}
	}

	// Convert map to contacts slice
	for jid, name := range contactMap {
		b.contacts = append(b.contacts, Contact{
			JID:  jid,
			Name: name, // For now use JID as name
		})
	}

	b.logger.Info(fmt.Sprintf("📞 Extraídos %d contactos únicos desde mensajes", len(b.contacts)))
}
