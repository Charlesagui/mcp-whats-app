@echo off
title WhatsApp - Compilar y Ejecutar
color 0C

cd /d C:\whatsapp-mcp-secure\whatsapp-bridge

echo ===============================================
echo    COMPILANDO BRIDGE PRIMERO
echo ===============================================
echo.

REM Configurar entorno
set CGO_ENABLED=1
set PATH=C:\TDM-GCC-64\bin;%PATH%

echo Limpiando compilaciones anteriores...
if exist "whatsapp-bridge.exe" del whatsapp-bridge.exe

echo.
echo Compilando...
go build -v -o whatsapp-bridge.exe main.go

if not exist "whatsapp-bridge.exe" (
    echo.
    echo ❌ ERROR DE COMPILACION
    echo.
    echo Posibles soluciones:
    echo 1. Instalar TDM-GCC: https://jmeubank.github.io/tdm-gcc/
    echo 2. Verificar que CGO_ENABLED=1
    echo 3. Ejecutar: go mod download
    echo.
    pause
    exit /b 1
)

echo ✅ Compilacion exitosa
echo.
echo ===============================================
echo    EJECUTANDO BRIDGE COMPILADO
echo ===============================================
echo.
echo ⚠️  Esta ventana permanecera abierta
echo ⚠️  El QR aparecera abajo - NO CERRAR
echo.

.\whatsapp-bridge.exe

echo.
echo ===============================================
echo    PROGRAMA DETENIDO
echo ===============================================
echo.
pause
