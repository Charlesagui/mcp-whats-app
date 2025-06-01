package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/mux"
	"go.mau.fi/whatsmeow/types"
	waProto "go.mau.fi/whatsmeow/binary/proto"
)

func (b *WhatsAppBridge) setupRoutes() *mux.Router {
	router := mux.NewRouter()

	// Middleware de autenticación
	router.Use(b.authMiddleware)

	// Rutas de la API
	api := router.PathPrefix("/api/v1").Subrouter()
	
	api.HandleFunc("/health", b.handleHealth).Methods("GET")
	api.HandleFunc("/messages", b.handleGetMessages).Methods("GET")
	api.HandleFunc("/messages", b.handleSendMessage).Methods("POST")
	api.HandleFunc("/contacts", b.handleGetContacts).Methods("GET")
	api.HandleFunc("/contacts/sync", b.handleSyncContacts).Methods("POST")
	api.HandleFunc("/chats", b.handleGetChats).Methods("GET")

	return router
}

func (b *WhatsAppBridge) authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		token := r.Header.Get("Authorization")
		if token != "Bearer "+b.config.AdminToken {
			b.sendErrorResponse(w, "Token no válido", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (b *WhatsAppBridge) handleHealth(w http.ResponseWriter, r *http.Request) {
	connected := false
	mode := "disconnected"
	
	if b.client != nil && b.client.IsConnected() {
		connected = true
		mode = "whatsapp_real"
	}

	response := APIResponse{
		Success: true,
		Data: map[string]interface{}{
			"status":         "healthy",
			"timestamp":      time.Now().UTC(),
			"connected":      connected,
			"messages_count": len(b.messages),
			"mode":          mode,
		},
	}
	b.sendJSONResponse(w, response)
}

func (b *WhatsAppBridge) handleGetMessages(w http.ResponseWriter, r *http.Request) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	chatJID := r.URL.Query().Get("chat_jid")
	limitStr := r.URL.Query().Get("limit")
	
	limit := 50 // default
	if limitStr != "" {
		if parsedLimit, err := strconv.Atoi(limitStr); err == nil {
			limit = parsedLimit
		}
	}

	var filteredMessages []Message
	for i := len(b.messages) - 1; i >= 0 && len(filteredMessages) < limit; i-- {
		msg := b.messages[i]
		if chatJID == "" || msg.ChatJID == chatJID {
			filteredMessages = append(filteredMessages, msg)
		}
	}

	response := APIResponse{
		Success: true,
		Data:    filteredMessages,
	}
	b.sendJSONResponse(w, response)
}

func (b *WhatsAppBridge) handleSendMessage(w http.ResponseWriter, r *http.Request) {
	var req SendMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		b.sendErrorResponse(w, "Formato JSON inválido", http.StatusBadRequest)
		return
	}

	// Validar campos requeridos
	if req.ChatJID == "" || req.Content == "" {
		b.sendErrorResponse(w, "chat_jid y content son requeridos", http.StatusBadRequest)
		return
	}

	// Verificar que WhatsApp esté conectado
	if b.client == nil || !b.client.IsConnected() {
		b.sendErrorResponse(w, "WhatsApp no está conectado", http.StatusServiceUnavailable)
		return
	}

	// Enviar mensaje REAL a WhatsApp
	chatJID, err := types.ParseJID(req.ChatJID)
	if err != nil {
		b.sendErrorResponse(w, "JID inválido", http.StatusBadRequest)
		return
	}

	msg := &waProto.Message{
		Conversation: &req.Content,
	}

	resp, err := b.client.SendMessage(context.Background(), chatJID, msg)
	if err != nil {
		b.logger.Error("Error enviando mensaje real:", err)
		b.sendErrorResponse(w, "Error enviando mensaje", http.StatusInternalServerError)
		return
	}

	// Guardar mensaje enviado en memoria también
	b.mu.Lock()
	newMessage := Message{
		ID:          resp.ID,
		ChatJID:     req.ChatJID,
		SenderJID:   "self",
		Content:     req.Content,
		Timestamp:   resp.Timestamp,
		MessageType: "text",
	}
	b.messages = append(b.messages, newMessage)
	b.mu.Unlock()

	b.logger.Info(fmt.Sprintf("📤 Mensaje enviado a WhatsApp: %s -> %s", req.ChatJID, req.Content))

	response := APIResponse{
		Success: true,
		Data: map[string]interface{}{
			"message_id": resp.ID,
			"timestamp":  resp.Timestamp,
			"mode":      "whatsapp_real",
		},
	}
	b.sendJSONResponse(w, response)
}

func (b *WhatsAppBridge) handleGetContacts(w http.ResponseWriter, r *http.Request) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	searchQuery := r.URL.Query().Get("search")
	
	var filteredContacts []Contact
	for _, contact := range b.contacts {
		if searchQuery == "" || 
		   strings.Contains(strings.ToLower(contact.Name), strings.ToLower(searchQuery)) ||
		   strings.Contains(contact.JID, searchQuery) {
			filteredContacts = append(filteredContacts, contact)
		}
	}

	response := APIResponse{
		Success: true,
		Data:    filteredContacts,
	}
	b.sendJSONResponse(w, response)
}

func (b *WhatsAppBridge) handleGetChats(w http.ResponseWriter, r *http.Request) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	// Agrupar mensajes por chat
	chatStats := make(map[string]map[string]interface{})
	
	for _, msg := range b.messages {
		if _, exists := chatStats[msg.ChatJID]; !exists {
			chatStats[msg.ChatJID] = map[string]interface{}{
				"chat_jid":      msg.ChatJID,
				"message_count": 0,
				"last_message":  msg.Timestamp,
			}
		}
		chatStats[msg.ChatJID]["message_count"] = chatStats[msg.ChatJID]["message_count"].(int) + 1
		if msg.Timestamp.After(chatStats[msg.ChatJID]["last_message"].(time.Time)) {
			chatStats[msg.ChatJID]["last_message"] = msg.Timestamp
		}
	}

	var chats []map[string]interface{}
	for _, stats := range chatStats {
		chats = append(chats, stats)
	}

	response := APIResponse{
		Success: true,
		Data:    chats,
	}
	b.sendJSONResponse(w, response)
}

// Funciones auxiliares
func (b *WhatsAppBridge) sendJSONResponse(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func (b *WhatsAppBridge) sendErrorResponse(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	response := APIResponse{
		Success: false,
		Error:   message,
	}
	json.NewEncoder(w).Encode(response)
}


func (b *WhatsAppBridge) handleSyncContacts(w http.ResponseWriter, r *http.Request) {
	// Verificar que WhatsApp esté conectado
	if b.client == nil || !b.client.IsConnected() {
		b.sendErrorResponse(w, "WhatsApp no está conectado", http.StatusServiceUnavailable)
		return
	}

	// Ejecutar sincronización en segundo plano
	go b.syncContacts()

	response := APIResponse{
		Success: true,
		Data: map[string]interface{}{
			"message": "Sincronización de contactos iniciada",
			"status":  "processing",
		},
	}
	b.sendJSONResponse(w, response)
}
