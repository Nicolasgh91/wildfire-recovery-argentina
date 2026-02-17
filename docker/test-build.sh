#!/bin/bash

# Docker Container Build Test Script
# Tests the fixes for frontend and nginx container build issues

set -e

echo "🔥 ForestGuard Docker Build Test"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
echo "🐳 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi
print_status "Docker is running"

# Check docker-compose files
echo ""
echo "📋 Checking configuration files..."

if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in docker/ directory"
    exit 1
fi
print_status "docker-compose.yml found"

if [ ! -f "nginx.conf" ]; then
    print_error "nginx.conf not found in docker/ directory"
    exit 1
fi
print_status "nginx.conf found"

# Test nginx configuration syntax
echo ""
echo "🔧 Testing nginx configuration..."
if docker run --rm nginx:alpine nginx -t -c /dev/stdin < nginx.conf > /dev/null 2>&1; then
    print_status "nginx.conf syntax is valid"
else
    print_error "nginx.conf has syntax errors"
    docker run --rm nginx:alpine nginx -t -c /dev/stdin < nginx.conf
    exit 1
fi

# Check frontend Dockerfile
echo ""
echo "🏗️  Checking frontend Dockerfile..."
if [ ! -f "../frontend/Dockerfile" ]; then
    print_error "Frontend Dockerfile not found"
    exit 1
fi
print_status "Frontend Dockerfile found"

# Check if frontend dist exists
if [ ! -d "../frontend/dist" ]; then
    print_warning "Frontend dist directory not found. Building frontend..."
    cd ../frontend
    npm ci
    npm run build
    cd ../docker
    print_status "Frontend built successfully"
else
    print_status "Frontend dist directory exists"
fi

# Test frontend build
echo ""
echo "📦 Testing frontend container build..."
if docker build -f ../frontend/Dockerfile -t forestguard-frontend-test ../frontend; then
    print_status "Frontend container build successful"
    
    # Test if frontend container serves files
    echo "🌐 Testing frontend container..."
    if docker run --rm -d -p 8080:80 --name frontend-test forestguard-frontend-test; then
        sleep 3
        if curl -f http://localhost:8080 > /dev/null 2>&1; then
            print_status "Frontend container serves files correctly"
        else
            print_error "Frontend container not serving files"
        fi
        docker stop frontend-test > /dev/null 2>&1 || true
        docker rm frontend-test > /dev/null 2>&1 || true
    fi
else
    print_error "Frontend container build failed"
    exit 1
fi

# Test API build if Dockerfile.api exists
if [ -f "../Dockerfile.api" ]; then
    echo ""
    echo "🔬 Testing API container build..."
    if docker build -f ../Dockerfile.api -t forestguard-api-test ..; then
        print_status "API container build successful"
    else
        print_error "API container build failed"
        exit 1
    fi
else
    print_warning "API Dockerfile not found, skipping API test"
fi

# Cleanup test images
echo ""
echo "🧹 Cleaning up test images..."
docker rmi forestguard-frontend-test > /dev/null 2>&1 || true
docker rmi forestguard-api-test > /dev/null 2>&1 || true
print_status "Test images cleaned up"

# Final summary
echo ""
echo "🎉 Build Test Summary"
echo "===================="
print_status "All critical components validated"
print_status "Container builds should work correctly"
echo ""
echo "Next steps:"
echo "1. Run 'docker-compose up --build' to start full stack"
echo "2. Access http://localhost for frontend"
echo "3. Access http://localhost/api/health for API"
echo ""
echo "📚 See build-fixes.md for detailed documentation"
