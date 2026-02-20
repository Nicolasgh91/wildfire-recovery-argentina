#!/bin/bash
# Docker Deployment Fix Script
# Run this script after starting Docker Desktop

echo "=== ForestGuard Docker Deployment Fix ==="
echo

echo "1. Restarting containers with new Redis configuration..."
docker compose restart api redis

echo
echo "2. Waiting 10 seconds for containers to start..."
sleep 10

echo
echo "3. Testing API health endpoint..."
curl -f http://localhost:8000/health

echo
echo "4. Testing fire episodes API endpoint..."
curl -s "http://localhost:8000/api/v1/fire-episodes?mode=active&page=1&page_size=5" | head -c 200

echo
echo "5. Checking API container logs..."
docker compose logs --tail=10 api

echo
echo "6. Checking Redis container logs..."
docker compose logs --tail=5 redis

echo
echo "=== Fix Complete ==="
echo "If you see Redis connection errors, the fix may need to be applied to other containers."
echo "Run: docker compose restart worker-ingestion worker-clustering worker-analysis celery-beat flower"
