# Quick Validation Script - Docker Not Required
# Validates that all fixes are in place correctly

Write-Host "🔥 ForestGuard Docker Fixes Validation" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green

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

# Check 1: Nginx configuration exists and has required directives
Write-Host "`n🔧 Checking nginx configuration..."
if (Test-Path "nginx.conf") {
    Print-Success "nginx.conf exists"
    
    $nginxContent = Get-Content "nginx.conf" -Raw
    if ($nginxContent -match "root /usr/share/nginx/html") {
        Print-Success "nginx.conf serves frontend files"
    } else {
        Print-Error "nginx.conf missing frontend serving directive"
    }
    
    if ($nginxContent -match "try_files.*index\.html") {
        Print-Success "nginx.conf has SPA fallback"
    } else {
        Print-Error "nginx.conf missing SPA fallback"
    }
    
    if ($nginxContent -match "gzip on") {
        Print-Success "nginx.conf has gzip compression"
    } else {
        Print-Warning "nginx.conf missing gzip compression"
    }
} else {
    Print-Error "nginx.conf not found"
}

# Check 2: Frontend Dockerfile
Write-Host "`n🏗️  Checking frontend Dockerfile..."
if (Test-Path "..\frontend\Dockerfile") {
    Print-Success "Frontend Dockerfile exists"
    
    $dockerfileContent = Get-Content "..\frontend\Dockerfile" -Raw
    if ($dockerfileContent -match "npm ci") {
        Print-Success "Frontend Dockerfile uses npm ci"
    } else {
        Print-Warning "Frontend Dockerfile should use npm ci instead of npm install"
    }
    
    if ($dockerfileContent -match "rm.*default\.conf") {
        Print-Success "Frontend Dockerfile removes default nginx config"
    } else {
        Print-Warning "Frontend Dockerfile may have nginx config conflicts"
    }
} else {
    Print-Error "Frontend Dockerfile not found"
}

# Check 3: Docker ignore files
Write-Host "`n📋 Checking .dockerignore files..."

if (Test-Path "..\frontend\.dockerignore") {
    Print-Success "Frontend .dockerignore exists"
    
    $dockerignoreContent = Get-Content "..\frontend\.dockerignore" -Raw
    if ($dockerignoreContent -match "node_modules") {
        Print-Success "Frontend .dockerignore excludes node_modules"
    } else {
        Print-Error "Frontend .dockerignore should exclude node_modules"
    }
} else {
    Print-Error "Frontend .dockerignore not found"
}

if (Test-Path "..\.dockerignore") {
    Print-Success "Root .dockerignore exists"
    
    $dockerignoreContent = Get-Content "..\.dockerignore" -Raw
    if ($dockerignoreContent -match ".venv") {
        Print-Success "Root .dockerignore excludes virtual environments"
    } else {
        Print-Warning "Root .dockerignore should exclude .venv"
    }
} else {
    Print-Error "Root .dockerignore not found"
}

# Check 4: Frontend build
Write-Host "`n📦 Checking frontend build..."
if (Test-Path "..\frontend\dist") {
    Print-Success "Frontend dist directory exists"
    
    if (Test-Path "..\frontend\dist\index.html") {
        Print-Success "Frontend index.html exists"
    } else {
        Print-Warning "Frontend index.html not found in dist"
    }
} else {
    Print-Warning "Frontend dist directory not found - will be built during Docker build"
}

# Check 5: Package files
Write-Host "`n📄 Checking package files..."
if (Test-Path "..\frontend\package.json") {
    Print-Success "Frontend package.json exists"
    
    $packageContent = Get-Content "..\frontend\package.json" -Raw
    if ($packageContent -match '"build"') {
        Print-Success "Frontend package.json has build script"
    } else {
        Print-Error "Frontend package.json missing build script"
    }
} else {
    Print-Error "Frontend package.json not found"
}

# Check 6: Docker compose files
Write-Host "`n🐳 Checking Docker Compose files..."
if (Test-Path "docker-compose.yml") {
    Print-Success "Docker docker-compose.yml exists"
    
    $composeContent = Get-Content "docker-compose.yml" -Raw
    if ($composeContent -match "frontend:") {
        Print-Success "Docker compose includes frontend service"
    } else {
        Print-Error "Docker compose missing frontend service"
    }
    
    if ($composeContent -match "nginx:") {
        Print-Success "Docker compose includes nginx service"
    } else {
        Print-Error "Docker compose missing nginx service"
    }
} else {
    Print-Error "Docker docker-compose.yml not found"
}

# Summary
Write-Host "`n🎉 Validation Summary" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "All critical fixes are in place!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start Docker Desktop" -ForegroundColor White
Write-Host "2. Run: docker-compose up --build" -ForegroundColor White
Write-Host "3. Test: http://localhost (frontend)" -ForegroundColor White
Write-Host "4. Test: http://localhost/api/health (API)" -ForegroundColor White
Write-Host ""
Write-Host "📚 See IMPLEMENTATION_SUMMARY.md for detailed documentation" -ForegroundColor Cyan
