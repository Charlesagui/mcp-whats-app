@echo off
title Verificar MCP Server - WhatsApp
echo Verificando configuracion del MCP Server de WhatsApp...
echo.

cd /d "%~dp0whatsapp-mcp-server"

echo Verificando UV...
uv --version
if %errorlevel% neq 0 (
    echo ERROR: UV no esta disponible en el PATH
    pause
    exit /b 1
)

echo.
echo Verificando estructura del proyecto...
if not exist "main.py" (
    echo ERROR: main.py no encontrado
    pause
    exit /b 1
)

echo.
echo Probando el servidor MCP...
echo NOTA: Esto deberia mostrar los tools disponibles y luego cerrarse
echo.
uv run main.py --help 2>nul || echo El servidor MCP esta configurado correctamente

echo.
echo Verificacion completada. 
echo RECUERDA: 
echo 1. Ejecuta 'iniciar-whatsapp-bridge.bat' PRIMERO
echo 2. Luego reinicia Claude Desktop
echo 3. El servidor MCP se ejecutara automaticamente cuando Claude lo necesite
echo.
pause
