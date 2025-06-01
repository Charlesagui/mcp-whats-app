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

	// Cargar configuración
	if err := bridge.loadConfig(); err != nil {
		log.Fatal("Error cargando configuración:", err)
	}

	// Configurar logging
	bridge.setupLogging()

	// Inicializar WhatsApp REAL
	if err := bridge.initWhatsApp(); err != nil {
		bridge.logger.Fatal("Error inicializando WhatsApp:", err)
	}

	// Configurar rutas HTTP
	router := bridge.setupRoutes()

	// Iniciar servidor HTTP
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

	// Esperar señal de cierre
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	bridge.logger.Info("Cerrando WhatsApp Bridge...")

	// Cerrar cliente de WhatsApp
	if bridge.client != nil {
		bridge.client.Disconnect()
	}

	// Cerrar servidor HTTP
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		bridge.logger.Error("Error cerrando servidor HTTP:", err)
	}

	bridge.logger.Info("WhatsApp Bridge cerrado correctamente")
}

func (b *WhatsAppBridge) loadConfig() error {
	// Cargar archivo .env
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

	// Crear directorio de logs si no existe
	if err := os.MkdirAll(b.config.LogPath, 0750); err != nil {
		b.logger.Error("Error creando directorio de logs:", err)
	}

	// Configurar formato de logs
	b.logger.SetFormatter(&logrus.JSONFormatter{
		TimestampFormat: time.RFC3339,
	})
}

func (b *WhatsAppBridge) initWhatsApp() error {
	// Crear directorio de autenticación
	authDir := "../auth"
	if err := os.MkdirAll(authDir, 0700); err != nil {
		return fmt.Errorf("error creando directorio de auth: %v", err)
	}

	// Configurar store de WhatsApp con SQLite persistente
	dbLog := waLog.Stdout("Database", "INFO", true)
	container, err := sqlstore.New(context.Background(), "sqlite3", "file:"+authDir+"/whatsapp.db?_foreign_keys=on", dbLog)
	if err != nil {
		return fmt.Errorf("error creando container de WhatsApp: %v", err)
	}

	// Obtener device store
	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		return fmt.Errorf("error obteniendo device store: %v", err)
	}

	// Configurar logging de WhatsApp
	clientLog := waLog.Stdout("Client", "INFO", true)

	// Crear cliente
	b.client = whatsmeow.NewClient(deviceStore, clientLog)

	// Configurar event handlers
	b.client.AddEventHandler(b.handleMessage)
	b.client.AddEventHandler(b.handleReceipt)
	b.client.AddEventHandler(b.handleConnected)

	// Conectar
	if b.client.Store.ID == nil {
		// Primera vez - mostrar QR
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
				// Mostrar QR visual en la terminal
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
		// Reconectar
		err = b.client.Connect()
		if err != nil {
			return fmt.Errorf("error reconectando a WhatsApp: %v", err)
		}
		b.logger.Info("🔄 Reconectado a WhatsApp existente")
	}

	b.logger.Info("✅ WhatsApp conectado correctamente")
	
	// Iniciar sincronización de contactos
	go b.syncContacts()
	
	return nil
}

// Funciones para almacenamiento en memoria
func (b *WhatsAppBridge) saveMessage(v *events.Message) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	// Extraer contenido del mensaje
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

	// Guardar en memoria
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


// Event handler para la conexión exitosa
func (b *WhatsAppBridge) handleConnected(evt interface{}) {
	b.logger.Info("🔗 WhatsApp conectado - sincronizando contactos...")
	go b.syncContacts()
}

// Sincronizar contactos desde WhatsApp
func (b *WhatsAppBridge) syncContacts() {
	if b.client == nil || !b.client.IsConnected() {
		b.logger.Warn("Cliente no conectado para sincronizar contactos")
		return
	}

	// Esperar un momento para que la conexión se estabilice
	time.Sleep(2 * time.Second)

	// Obtener contactos usando whatsmeow
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Intentar obtener contactos del store
	contacts, err := b.client.Store.Contacts.GetAllContacts(ctx)
	if err != nil {
		b.logger.Error("Error obteniendo contactos del store:", err)
		// Intentar método alternativo - obtener de conversaciones recientes
		b.syncContactsFromChats()
		return
	}

	b.mu.Lock()
	defer b.mu.Unlock()

	// Limpiar contactos existentes
	b.contacts = make([]Contact, 0)

	// Convertir y guardar contactos
	for jid, contact := range contacts {
		if contact.Found && contact.PushName != "" {
			b.contacts = append(b.contacts, Contact{
				JID:  jid.String(),
				Name: contact.PushName,
			})
		} else if contact.Found && contact.BusinessName != "" {
			b.contacts = append(b.contacts, Contact{
				JID:  jid.String(),
				Name: contact.BusinessName,
			})
		}
	}

	b.logger.Info(fmt.Sprintf("📞 Sincronizados %d contactos", len(b.contacts)))
}

// Método alternativo: sincronizar contactos desde chats recientes
func (b *WhatsAppBridge) syncContactsFromChats() {
	if b.client == nil || !b.client.IsConnected() {
		return
	}

	// Obtener conversaciones recientes - usar método correcto de whatsmeow
	// Por ahora, usar un método alternativo basado en mensajes almacenados
	b.syncContactsFromMessages()
}



// Método alternativo: sincronizar contactos desde mensajes almacenados
func (b *WhatsAppBridge) syncContactsFromMessages() {
	b.mu.Lock()
	defer b.mu.Unlock()

	// Limpiar contactos existentes
	b.contacts = make([]Contact, 0)
	
	// Crear un mapa para evitar duplicados
	contactMap := make(map[string]string)

	// Procesar mensajes para extraer contactos únicos
	for _, msg := range b.messages {
		if msg.SenderJID != "self" && msg.SenderJID != "" {
			// Extraer el número de teléfono del JID
			if _, exists := contactMap[msg.SenderJID]; !exists {
				// Usar el número como nombre temporal (se puede mejorar después)
				contactMap[msg.SenderJID] = msg.SenderJID
			}
		}
	}

	// Convertir mapa a slice de contactos
	for jid, name := range contactMap {
		b.contacts = append(b.contacts, Contact{
			JID:  jid,
			Name: name, // Por ahora usar el JID como nombre
		})
	}

	b.logger.Info(fmt.Sprintf("📞 Extraídos %d contactos únicos desde mensajes", len(b.contacts)))
}
