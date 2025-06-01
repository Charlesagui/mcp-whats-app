@echo off
echo === WhatsApp MCP Secure - Inicio Rápido ===
echo.

REM Verificar si existen los directorios necesarios
if not exist "data" (
    echo Error: Ejecuta primero el script de configuración
    echo Comando: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -All
    pause
    exit /b 1
)

if not exist ".env" (
    echo Error: Archivo .env no encontrado
    echo Ejecuta el script de configuración primero
    pause
    exit /b 1
)

echo Iniciando WhatsApp MCP Secure...
echo.

REM Iniciar WhatsApp Bridge en ventana separada
echo Iniciando WhatsApp Bridge...
start "WhatsApp Bridge" cmd /k "cd whatsapp-bridge && go run main.go"

REM Esperar unos segundos para que el bridge inicie
timeout /t 3 /nobreak >nul

REM Iniciar MCP Server en ventana separada
echo Iniciando MCP Server...
start "MCP Server" cmd /k "cd mcp-server && venv\Scripts\activate && python main.py"

echo.
echo ✓ Servicios iniciados
echo ✓ WhatsApp Bridge ejecutándose en puerto 8081
echo ✓ MCP Server ejecutándose
echo.
echo Próximos pasos:
echo 1. Escanea el código QR con tu teléfono cuando aparezca
echo 2. Configura Claude Desktop con el archivo de configuración
echo 3. Reinicia Claude Desktop
echo.
echo Presiona cualquier tecla para continuar...
pause >nul
