# Script de configuración inicial para WhatsApp MCP Secure
# Ejecutar como administrador

param(
    [switch]$InstallDependencies,
    [switch]$GenerateKeys,
    [switch]$SetupDirectories,
    [switch]$All
)

Write-Host "=== WhatsApp MCP Secure - Script de Configuración ===" -ForegroundColor Green

if ($All) {
    $InstallDependencies = $true
    $GenerateKeys = $true
    $SetupDirectories = $true
}

# Función para generar claves seguras
function Generate-SecureKey {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::Create()
    $rng.GetBytes($bytes)
    return [System.Convert]::ToBase64String($bytes)
}

# Configurar directorios con permisos seguros
if ($SetupDirectories) {
    Write-Host "Configurando directorios..." -ForegroundColor Yellow
    
    $directories = @("data", "auth", "logs", "backups")
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "✓ Creado directorio: $dir" -ForegroundColor Green
        }
        
        # Configurar permisos restrictivos
        $acl = Get-Acl $dir
        $acl.SetAccessRuleProtection($true, $false)
        $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
            "FullControl",
            "ContainerInherit,ObjectInherit",
            "None",
            "Allow"
        )
        $acl.SetAccessRule($accessRule)
        Set-Acl -Path $dir -AclObject $acl
    }
}

# Generar claves de cifrado
if ($GenerateKeys) {
    Write-Host "Generando claves de cifrado..." -ForegroundColor Yellow
    
    if (!(Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Archivo .env creado desde plantilla" -ForegroundColor Green
    }
    
    # Generar claves
    $adminToken = Generate-SecureKey
    $dbKey = Generate-SecureKey
    $backupKey = Generate-SecureKey
    
    # Actualizar archivo .env
    $envContent = Get-Content ".env"
    $envContent = $envContent -replace "your_secure_admin_token_here", $adminToken
    $envContent = $envContent -replace "your_database_encryption_key_here", $dbKey
    $envContent = $envContent -replace "your_backup_encryption_key_here", $backupKey
    
    Set-Content ".env" $envContent
    Write-Host "✓ Claves de cifrado generadas y configuradas" -ForegroundColor Green
    Write-Host "⚠️  IMPORTANTE: Guarda estas claves en un lugar seguro" -ForegroundColor Red
}

# Instalar dependencias
if ($InstallDependencies) {
    Write-Host "Instalando dependencias..." -ForegroundColor Yellow
    
    # Verificar Go
    try {
        $goVersion = go version
        Write-Host "✓ Go detectado: $goVersion" -ForegroundColor Green
    } catch {
        Write-Host "✗ Go no encontrado. Instala Go desde https://golang.org/" -ForegroundColor Red
        exit 1
    }
    
    # Verificar Python
    try {
        $pythonVersion = python --version
        Write-Host "✓ Python detectado: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "✗ Python no encontrado. Instala Python desde https://python.org/" -ForegroundColor Red
        exit 1
    }
    
    # Instalar dependencias de Go
    Write-Host "Instalando dependencias de Go..." -ForegroundColor Cyan
    Set-Location "whatsapp-bridge"
    go mod tidy
    go mod download
    Set-Location ".."
    Write-Host "✓ Dependencias de Go instaladas" -ForegroundColor Green
    
    # Crear entorno virtual Python
    Write-Host "Configurando entorno virtual Python..." -ForegroundColor Cyan
    Set-Location "mcp-server"
    if (!(Test-Path "venv")) {
        python -m venv venv
        Write-Host "✓ Entorno virtual creado" -ForegroundColor Green
    }
    
    # Activar entorno e instalar dependencias
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    deactivate
    Set-Location ".."
    Write-Host "✓ Dependencias de Python instaladas" -ForegroundColor Green
}

Write-Host "`n=== Configuración completada ===" -ForegroundColor Green
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "1. Ejecutar WhatsApp Bridge: cd whatsapp-bridge && go run main.go" -ForegroundColor White
Write-Host "2. En otra terminal, ejecutar MCP Server: cd mcp-server && .\venv\Scripts\Activate.ps1 && python main.py" -ForegroundColor White
Write-Host "3. Escanear código QR con tu teléfono" -ForegroundColor White
Write-Host "4. Configurar Claude Desktop con el archivo de configuración" -ForegroundColor White
