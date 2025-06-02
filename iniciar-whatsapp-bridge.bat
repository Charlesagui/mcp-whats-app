@echo off
title WhatsApp Bridge - Go Server
echo Iniciando WhatsApp Bridge...
echo.
echo IMPORTANTE: 
echo - La primera vez tendras que escanear un codigo QR con tu telefono
echo - Mantén esta ventana abierta mientras uses WhatsApp MCP
echo - Para detener: presiona Ctrl+C
echo.
pause

cd /d "C:\Users\aguia\Desktop\mi-whatsapp-mcp\whatsapp-bridge"
go run main.go

echo.
echo El bridge de WhatsApp se ha detenido.
pause
