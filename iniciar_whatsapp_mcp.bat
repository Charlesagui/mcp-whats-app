@echo off
title WhatsApp MCP - Iniciador Completo
color 0A
chcp 65001 >nul

echo.
echo ========================================
echo     WHATSAPP MCP - INICIADOR UNICO
echo ========================================
echo.

REM Verificar proyecto
if not exist "C:\Users\aguia\mcp-whats-app\.env" (
    echo ❌ Error: Proyecto no encontrado
    echo Verifica la ruta: C:\Users\aguia\mcp-whats-app
    pause
    exit /b 1
)

echo ✅ Proyecto encontrado
echo.

REM Verificar dependencias
echo 🔍 Verificando dependencias...

go version >nul 2>&1
if errorlevel 1 (
    echo ❌ Go no instalado
    pause
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no instalado  
    pause
    exit /b 1
)

echo ✅ Dependencias verificadas
echo.

REM Crear directorios
if not exist "C:\Users\aguia\mcp-whats-app\logs" mkdir "C:\Users\aguia\mcp-whats-app\logs"
if not exist "C:\Users\aguia\mcp-whats-app\data" mkdir "C:\Users\aguia\mcp-whats-app\data"

REM Matar procesos previos
echo 🧹 Limpiando procesos previos...
taskkill /f /im "whatsapp-bridge.exe" >nul 2>&1
taskkill /f /im "python.exe" >nul 2>&1
timeout /t 2 /nobreak >nul

REM Verificar/compilar bridge
echo 🔨 Verificando WhatsApp Bridge...
if not exist "C:\Users\aguia\mcp-whats-app\whatsapp-bridge\whatsapp-bridge.exe" (
    echo Compilando bridge...
    cd C:\Users\aguia\mcp-whats-app\whatsapp-bridge
    set CGO_ENABLED=1
    go build -o whatsapp-bridge.exe .
    if errorlevel 1 (
        echo ❌ Error compilando bridge
        pause
        exit /b 1
    )
    echo ✅ Bridge compilado
) else (
    echo ✅ Bridge ya existe
)

echo.
echo 🚀 Iniciando servicios...
echo.

REM Iniciar WhatsApp Bridge
echo 📱 Iniciando WhatsApp Bridge (Puerto 8081)...
start "🔗 WhatsApp Bridge - Puerto 8081" cmd /k "cd C:\Users\aguia\mcp-whats-app\whatsapp-bridge && echo 📱 WHATSAPP BRIDGE INICIADO && echo Esperando conexion... && echo. && whatsapp-bridge.exe"

REM Esperar un momento
timeout /t 3 /nobreak >nul

REM Iniciar MCP Server  
echo 🤖 Iniciando MCP Server (Puerto 8080)...
start "🔧 MCP Server - Puerto 8080" cmd /k "cd C:\Users\aguia\mcp-whats-app\mcp-server && echo 🤖 MCP SERVER INICIADO && echo Conectando con Claude Desktop... && echo. && python main_fixed.py"

echo.
echo ✅ SERVICIOS INICIADOS CORRECTAMENTE
echo.
echo 📋 ESTADO:
echo    🔗 WhatsApp Bridge: Puerto 8081 (ventana separada)
echo    🤖 MCP Server:      Puerto 8080 (ventana separada)  
echo.
echo 📱 CONECTAR WHATSAPP:
echo    1. Ve a la ventana "WhatsApp Bridge - Puerto 8081"
echo    2. Escanea el código QR con tu teléfono:
echo       • WhatsApp ^> Dispositivos Vinculados
echo       • "Vincular un dispositivo"  
echo       • Escanear el QR visual
echo.
echo 🔧 CONFIGURAR CLAUDE:
echo    3. Ejecuta: python configure_claude_simple.py
echo    4. Reinicia Claude Desktop
echo    5. Prueba: "¿Cuál es el estado de WhatsApp?"
echo.
echo ⚙️  OPCIONES:
echo    [1] Configurar Claude Desktop automaticamente
echo    [2] Verificar estado de servicios
echo    [3] Abrir carpeta del proyecto
echo    [4] Detener todos los servicios
echo    [5] Ver logs en tiempo real
echo    [6] Salir
echo.

:menu
set /p choice="Selecciona una opcion (1-6): "

if "%choice%"=="1" (
    echo.
    echo 🔧 Configurando Claude Desktop...
    cd C:\Users\aguia\mcp-whats-app\mcp-server
    python configure_claude_simple.py
    echo.
    echo ✅ Configuracion completada
    echo 🔄 REINICIA CLAUDE DESKTOP AHORA
    echo.
    goto menu
)

if "%choice%"=="2" (
    echo.
    echo 🔍 Verificando servicios...
    echo.
    echo WhatsApp Bridge:
    tasklist | findstr "whatsapp-bridge.exe" && echo ✅ Bridge ejecutandose || echo ❌ Bridge no ejecutandose
    echo.
    echo MCP Server:
    tasklist | findstr "python.exe" && echo ✅ MCP Server ejecutandose || echo ❌ MCP Server no ejecutandose
    echo.
    echo Probando conexion al Bridge...
    powershell -Command "try { $headers = @{'Authorization'='Bearer a8f5c2e1b9d4f7e3a6c8b5d9e2f4a7c1b8e5f2a9c6d3e7f1a4b8c5d9e2f6a3c7'}; Invoke-WebRequest -Uri 'http://localhost:8081/api/v1/health' -Headers $headers -TimeoutSec 5 | Out-Null; Write-Host '✅ Bridge responde correctamente' } catch { Write-Host '❌ Bridge no responde' }"
    echo.
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo 📁 Abriendo carpeta del proyecto...
    explorer C:\Users\aguia\mcp-whats-app
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo 🛑 Deteniendo servicios...
    taskkill /f /im "whatsapp-bridge.exe" >nul 2>&1
    taskkill /f /im "python.exe" >nul 2>&1
    echo ✅ Servicios detenidos
    echo.
    goto menu
)

if "%choice%"=="5" (
    echo.
    echo 📋 Abriendo logs...
    if exist "C:\Users\aguia\mcp-whats-app\logs" (
        explorer C:\Users\aguia\mcp-whats-app\logs
    ) else (
        echo ❌ No hay logs disponibles aun
    )
    goto menu
)

if "%choice%"=="6" (
    echo.
    echo 👋 Cerrando iniciador...
    echo Los servicios seguiran ejecutandose en segundo plano.
    echo Para detenerlos completamente, usa la opcion 4.
    echo.
    pause
    exit /b 0
)

echo ❌ Opcion invalida
goto menu
