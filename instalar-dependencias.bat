@echo off
title Instalar Dependencias - WhatsApp MCP
echo Instalando dependencias para WhatsApp MCP...
echo.

echo === Instalando dependencias Go ===
cd /d "C:\Users\aguia\Desktop\mi-whatsapp-mcp\whatsapp-bridge"
go mod tidy
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de dependencias Go
    pause
    exit /b 1
)

echo.
echo === Verificando dependencias Python ===
cd /d "C:\Users\aguia\Desktop\mi-whatsapp-mcp\whatsapp-mcp-server"
uv sync
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de dependencias Python
    pause
    exit /b 1
)

echo.
echo === Verificando CGO ===
go env CGO_ENABLED
echo.

echo ✅ Todas las dependencias instaladas correctamente
echo.
echo Proximos pasos:
echo 1. Ejecuta 'iniciar-whatsapp-bridge.bat'
echo 2. Escanea el codigo QR con tu telefono
echo 3. Reinicia Claude Desktop
echo 4. ¡Ya puedes usar WhatsApp en Claude!
echo.
pause
