@echo off
title WhatsApp MCP - Instalador Dependencias
color 0A

echo ===============================================
echo    INSTALANDO DEPENDENCIAS GO
echo ===============================================
echo.

cd /d C:\whatsapp-mcp-secure\whatsapp-bridge

echo Verificando Go...
go version
if errorlevel 1 (
    echo Error: Go no instalado
    pause
    exit /b 1
)

echo.
echo Descargando dependencias...
echo.

REM Limpiar cache de modulos
go clean -modcache

REM Descargar dependencias
go mod tidy
go mod download

echo.
echo Verificando compilacion...
go build -o test.exe main.go

if exist "test.exe" (
    echo ✓ Compilacion exitosa
    del test.exe
) else (
    echo ✗ Error en compilacion
    echo.
    echo Intentando instalar dependencias individuales...
    
    go get github.com/gorilla/mux@v1.8.1
    go get github.com/joho/godotenv@v1.5.1
    go get github.com/mattn/go-sqlite3@v1.14.28
    go get github.com/mdp/qrterminal@v1.0.1
    go get github.com/sirupsen/logrus@v1.9.3
    go get go.mau.fi/whatsmeow@latest
    
    echo.
    echo Reintentando compilacion...
    go build -o test.exe main.go
    
    if exist "test.exe" (
        echo ✓ Compilacion exitosa tras reinstalacion
        del test.exe
    ) else (
        echo ✗ Error persistente
        echo Verifica que tengas GCC instalado
    )
)

echo.
echo ===============================================
echo    LISTO PARA EJECUTAR
echo ===============================================
echo.
pause
