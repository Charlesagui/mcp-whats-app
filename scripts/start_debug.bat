@echo off
title WhatsApp MCP Debug - No Auto-Close
color 0A

echo ===============================================
echo      WHATSAPP MCP - MODO DEBUG
echo ===============================================
echo.

REM Cambiar al directorio del proyecto
cd /d C:\whatsapp-mcp-secure

REM Verificar que existe el proyecto
if not exist ".env" (
    echo Error: Archivo .env no encontrado
    echo.
    pause
    exit /b 1
)

echo Verificando Go...
go version >nul 2>&1
if errorlevel 1 (
    echo Go no instalado
    pause
    exit /b 1
)

echo Go OK
echo.

echo ===============================================
echo   INICIANDO WHATSAPP BRIDGE - NO SE CIERRA
echo ===============================================
echo.
echo IMPORTANTE: Esta ventana NO se cerrara automaticamente
echo Para detener el servidor: Ctrl+C
echo.

REM Matar procesos previos
taskkill /f /im "go.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

echo Iniciando bridge en modo debug...
echo.

REM Ir al directorio del bridge y ejecutar
cd whatsapp-bridge

REM Ejecutar con pausa al final para debug
go run main.go
echo.
echo ===============================================
echo   EL PROGRAMA HA TERMINADO
echo ===============================================
echo.
echo Si se cerro muy rapido, revisa los errores arriba
echo.
pause
