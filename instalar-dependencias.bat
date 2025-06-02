@echo off
title Instalar Dependencias - WhatsApp MCP
echo Instalando dependencias para WhatsApp MCP...
echo.

echo === Instalando dependencias Go ===
cd /d "%~dp0whatsapp-bridge"
go mod tidy
if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion de dependencias Go
    pause
    exit /b 1
)

echo.
echo === Verificando dependencias Python ===
cd /d "%~dp0whatsapp-mcp-server"
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

echo === Creando archivo .env si no existe ===
cd /d "%~dp0"
if not exist ".env" (
    copy ".env.example" ".env"
    echo Archivo .env creado desde .env.example
    echo REVISA Y AJUSTA las configuraciones en .env si es necesario
) else (
    echo Archivo .env ya existe
)

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
