@echo off
title WhatsApp MCP Secure - Iniciador
color 0A

echo.
echo ===============================================
echo      WHATSAPP MCP SECURE - INICIADOR  
echo ===============================================
echo.

REM Verificar que existe el proyecto
if not exist "C:\Users\aguia\mcp-whats-app\.env" (
    echo Error: Proyecto no encontrado en C:\Users\aguia\mcp-whats-app
    echo.
    echo Necesitas configurar el proyecto primero
    echo.
    pause
    exit /b 1
)

echo Proyecto encontrado
echo Verificando configuracion...

REM Verificar Go
go version >nul 2>&1
if errorlevel 1 (
    echo Go no esta instalado. Descarga desde: https://golang.org/
    pause
    exit /b 1
)

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python no esta instalado. Descarga desde: https://python.org/
    pause
    exit /b 1
)

echo Dependencias verificadas
echo.

echo Compilando WhatsApp Bridge...
cd C:\Users\aguia\mcp-whats-app\whatsapp-bridge
set CGO_ENABLED=1
set PATH=C:\TDM-GCC-64\bin;%PATH%
go build -o whatsapp-bridge.exe .
if errorlevel 1 (
    echo Error compilando el bridge
    pause
    exit /b 1
)

echo Bridge compilado exitosamente
echo.

echo Iniciando servicios...
echo.

REM Matar procesos previos si existen
taskkill /f /im "whatsapp-bridge.exe" >nul 2>&1
taskkill /f /im "python.exe" >nul 2>&1

REM Crear directorio de logs si no existe
if not exist "C:\Users\aguia\mcp-whats-app\logs" mkdir "C:\Users\aguia\mcp-whats-app\logs"

echo Iniciando WhatsApp Bridge...
start "WhatsApp Bridge - Puerto 8081" cmd /c "cd C:\Users\aguia\mcp-whats-app\whatsapp-bridge && whatsapp-bridge.exe"

echo Esperando que el bridge inicie...
timeout /t 5 /nobreak >nul

echo Iniciando MCP Server...
start "MCP Server - Puerto 8080" cmd /c "cd C:\Users\aguia\mcp-whats-app\mcp-server && python main_fixed.py"

echo.
echo Servicios iniciados correctamente!
echo.
echo ESTADO DE SERVICIOS:
echo    - WhatsApp Bridge: Puerto 8081 (ventana separada)
echo    - MCP Server:      Puerto 8080 (ventana separada)
echo.
echo CONECTAR WHATSAPP:
echo    1. Ve a la ventana "WhatsApp Bridge - Puerto 8081"
echo    2. Si ves un codigo QR VISUAL (cuadraditos), escanealo con tu telefono:
echo       - WhatsApp ^> Configuracion ^> Dispositivos Vinculados
echo       - "Vincular un dispositivo"
echo       - Escanear el codigo QR VISUAL (no el texto largo)
echo    3. Una vez conectado, WhatsApp estara listo
echo.
echo NOTA: Si ves texto largo en lugar del QR visual, 
echo       cierra la ventana del bridge y reinicia este script.
echo.
echo VERIFICAR ESTADO:
echo    - Logs en: C:\Users\aguia\mcp-whats-app\logs\
echo    - Bridge: http://localhost:8081/api/v1/health
echo    - Para detener: Cierra las ventanas del bridge y MCP server
echo.

:menu
echo ===============================================
echo    Que quieres hacer?
echo ===============================================
echo.
echo [1] Ver estado del Bridge
echo [2] Ver estado del MCP Server  
echo [3] Verificar salud del sistema
echo [4] Configurar Claude Desktop
echo [5] Abrir carpeta del proyecto
echo [6] Detener servicios
echo [7] Salir
echo.
set /p choice="Selecciona una opcion (1-7): "

if "%choice%"=="1" (
    echo.
    echo Verificando estado del Bridge...
    tasklist | findstr "whatsapp-bridge.exe"
    if errorlevel 1 (
        echo Bridge no esta ejecutandose
    ) else (
        echo Bridge ejecutandose correctamente
    )
    echo.
    goto menu
)

if "%choice%"=="2" (
    echo.
    echo Verificando estado del MCP Server...
    tasklist | findstr "python.exe"
    if errorlevel 1 (
        echo MCP Server no esta ejecutandose
    ) else (
        echo MCP Server ejecutandose correctamente
        echo Nota: El MCP Server real no muestra menu interactivo
        echo       Se conecta directamente con Claude Desktop
    )
    echo.
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo Verificando salud del sistema...
    powershell -Command "try { $headers = @{'Authorization'='Bearer a8f5c2e1b9d4f7e3a6c8b5d9e2f4a7c1b8e5f2a9c6d3e7f1a4b8c5d9e2f6a3c7'}; Invoke-WebRequest -Uri 'http://localhost:8081/api/v1/health' -Headers $headers -TimeoutSec 5 | Out-Null; Write-Host 'Bridge responde correctamente' } catch { Write-Host 'Bridge no responde' }"
    echo.
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo Configurando Claude Desktop...
    cd C:\Users\aguia\mcp-whats-app\mcp-server
    python configure_claude.py
    echo.
    goto menu
)

if "%choice%"=="5" (
    echo.
    echo Abriendo carpeta del proyecto...
    explorer C:\Users\aguia\mcp-whats-app
    goto menu
)

if "%choice%"=="6" (
    echo.
    echo Deteniendo servicios...
    taskkill /f /im "whatsapp-bridge.exe" >nul 2>&1
    taskkill /f /im "python.exe" >nul 2>&1
    echo Servicios detenidos
    echo.
    goto menu
)

if "%choice%"=="7" (
    echo.
    echo Hasta luego!
    echo Los servicios seguiran ejecutandose en segundo plano.
    echo Para detenerlos completamente, usa la opcion 6.
    echo.
    pause
    exit /b 0
)

echo Opcion invalida
goto menu
