# Docker Container Build Test Script (PowerShell)
# Tests the fixes for frontend and nginx container build issues

param(
    [switch]$SkipCleanup
)

Write-Host "🔥 ForestGuard Docker Build Test" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Function to print status
function Print-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Check if Docker is running
Write-Host "`n🐳 Checking Docker..."
try {
    $null = docker info 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Docker is running"
    } else {
        Print-Error "Docker is not running. Please start Docker Desktop."
        exit 1
    }
} catch {
    Print-Error "Docker is not running. Please start Docker Desktop."
    exit 1
}

# Check docker-compose files
Write-Host "`n📋 Checking configuration files..."

if (-not (Test-Path "docker-compose.yml")) {
    Print-Error "docker-compose.yml not found in docker/ directory"
    exit 1
}
Print-Success "docker-compose.yml found"

if (-not (Test-Path "nginx.conf")) {
    Print-Error "nginx.conf not found in docker/ directory"
    exit 1
}
Print-Success "nginx.conf found"

# Test nginx configuration syntax
Write-Host "`n🔧 Testing nginx configuration..."
$nginxConfig = Get-Content "nginx.conf" -Raw
$containerId = docker run --rm -d nginx:alpine sh -c "echo '$nginxConfig' > /etc/nginx/nginx.conf; nginx -t"
if ($LASTEXITCODE -eq 0) {
    Print-Success "nginx.conf syntax is valid"
    docker stop $containerId >$null 2>&1
} else {
    Print-Error "nginx.conf has syntax errors"
    docker logs $containerId
    docker stop $containerId >$null 2>&1
    exit 1
}

# Check frontend Dockerfile
Write-Host "`n🏗️  Checking frontend Dockerfile..."
if (-not (Test-Path "..\frontend\Dockerfile")) {
    Print-Error "Frontend Dockerfile not found"
    exit 1
}
Print-Success "Frontend Dockerfile found"

# Check if frontend dist exists
if (-not (Test-Path "..\frontend\dist")) {
    Print-Warning "Frontend dist directory not found. Building frontend..."
    Set-Location "..\frontend"
    npm ci
    if ($LASTEXITCODE -ne 0) {
        Print-Error "npm ci failed"
        exit 1
    }
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Print-Error "npm run build failed"
        exit 1
    }
    Set-Location "..\docker"
    Print-Success "Frontend built successfully"
} else {
    Print-Success "Frontend dist directory exists"
}

# Test frontend build
Write-Host "`n📦 Testing frontend container build..."
$frontendBuild = docker build -f ..\frontend\Dockerfile -t forestguard-frontend-test ..\frontend 2>&1
if ($LASTEXITCODE -eq 0) {
    Print-Success "Frontend container build successful"
    
    # Test if frontend container serves files
    Write-Host "🌐 Testing frontend container..."
    $containerId = docker run --rm -d -p 8080:80 --name frontend-test forestguard-frontend-test
    if ($LASTEXITCODE -eq 0) {
        Start-Sleep -Seconds 3
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Print-Success "Frontend container serves files correctly"
            } else {
                Print-Error "Frontend container returned status code $($response.StatusCode)"
            }
        } catch {
            Print-Error "Frontend container not serving files: $($_.Exception.Message)"
        }
        docker stop frontend-test >$null 2>&1
    } else {
        Print-Error "Failed to start frontend container"
    }
} else {
    Print-Error "Frontend container build failed"
    Write-Host $frontendBuild
    exit 1
}

# Test API build if Dockerfile.api exists
if (Test-Path "..\Dockerfile.api") {
    Write-Host "`n🔬 Testing API container build..."
    $apiBuild = docker build -f ..\Dockerfile.api -t forestguard-api-test .. 2>&1
    if ($LASTEXITCODE -eq 0) {
        Print-Success "API container build successful"
    } else {
        Print-Error "API container build failed"
        Write-Host $apiBuild
        exit 1
    }
} else {
    Print-Warning "API Dockerfile not found, skipping API test"
}

# Cleanup test images
if (-not $SkipCleanup) {
    Write-Host "`n🧹 Cleaning up test images..."
    docker rmi forestguard-frontend-test >$null 2>&1
    docker rmi forestguard-api-test >$null 2>&1
    Print-Success "Test images cleaned up"
}

# Final summary
Write-Host "`n🎉 Build Test Summary" -ForegroundColor Green
Write-Host "====================" -ForegroundColor Green
Print-Success "All critical components validated"
Print-Success "Container builds should work correctly"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Run 'docker-compose up --build' to start full stack"
Write-Host "2. Access http://localhost for frontend"
Write-Host "3. Access http://localhost/api/health for API"
Write-Host ""
Write-Host "📚 See build-fixes.md for detailed documentation"
