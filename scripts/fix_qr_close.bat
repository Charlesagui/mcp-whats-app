@echo off
title WhatsApp Bridge - Solucion Paso a Paso
color 0B

echo ===============================================
echo    SOLUCION: BRIDGE QR SE CIERRA RAPIDO
echo ===============================================
echo.

cd /d C:\whatsapp-mcp-secure

echo Paso 1: Verificando entorno...
echo.

REM Verificar Go
go version
if errorlevel 1 (
    echo ❌ Go no instalado. Instala desde: https://golang.org/
    pause
    exit /b 1
)
echo ✅ Go instalado

REM Verificar GCC (necesario para SQLite)
gcc --version >nul 2>&1
if errorlevel 1 (
    echo ❌ GCC no encontrado
    echo Instalando TDM-GCC...
    set PATH=C:\TDM-GCC-64\bin;%PATH%
    gcc --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Instala TDM-GCC desde: https://jmeubank.github.io/tdm-gcc/
        pause
        exit /b 1
    )
)
echo ✅ GCC disponible

echo.
echo Paso 2: Configurando variables de entorno...
set CGO_ENABLED=1
set PATH=C:\TDM-GCC-64\bin;%PATH%
echo ✅ CGO_ENABLED=1

echo.
echo Paso 3: Instalando dependencias...
cd whatsapp-bridge
go mod tidy
if errorlevel 1 (
    echo ❌ Error en go mod tidy
    pause
    exit /b 1
)
echo ✅ Dependencias sincronizadas

echo.
echo Paso 4: Verificando compilacion...
go build -o whatsapp-bridge.exe main.go
if not exist "whatsapp-bridge.exe" (
    echo ❌ Error de compilacion. Errores comunes:
    echo - SQLite necesita CGO_ENABLED=1
    echo - Falta compilador C (GCC)
    echo - Problemas de red con dependencias
    echo.
    pause
    exit /b 1
)
echo ✅ Compilacion exitosa

echo.
echo Paso 5: Ejecutando bridge con logs detallados...
echo ===============================================
echo    ⚠️  NO CIERRES ESTA VENTANA MANUALMENTE
echo    El QR aparecera abajo - mantén abierto!
echo ===============================================
echo.

REM Ejecutar con variables de entorno correctas
.\whatsapp-bridge.exe

echo.
echo ===============================================
echo   PROGRAMA TERMINADO - REVISION DE ERRORES
echo ===============================================
echo.
echo Si el QR se cerro rapido, el error esta arriba ⬆️
echo Errores comunes:
echo - Base de datos corrupta (borra data/whatsapp.db)
echo - Puerto 8081 ocupado (usar netstat -an)
echo - Permisos de escritura
echo.
pause
