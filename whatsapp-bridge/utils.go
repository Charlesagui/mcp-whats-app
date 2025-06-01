package main

import (
	"os"
	"strconv"
	
	"go.mau.fi/whatsmeow/types/events"
)

// Helper functions for the WhatsApp bridge

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

// Event handlers for WhatsApp
func (b *WhatsAppBridge) handleMessage(evt interface{}) {
	switch v := evt.(type) {
	case *events.Message:
		// Save message to storage
		if err := b.saveMessage(v); err != nil {
			b.logger.Error("Error guardando mensaje:", err)
		}
	}
}

func (b *WhatsAppBridge) handleReceipt(evt interface{}) {
	switch v := evt.(type) {
	case *events.Receipt:
		b.logger.Debug("Receipt recibido:", v.MessageIDs)
	}
}
