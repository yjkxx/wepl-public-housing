#!/bin/bash

# Health Check Test Script
# This script tests if your container health checks work correctly

echo "🏥 Testing Container Health Checks"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Build the image
echo "📦 Building updated Docker image..."
docker build -t demo-container-health-test . > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo "✅ Docker image built successfully"

# Test run the container
echo "🚀 Starting container for health check testing..."
CONTAINER_ID=$(docker run -d -p 8082:80 demo-container-health-test)

if [ $? -ne 0 ]; then
    echo "❌ Failed to start container"
    exit 1
fi

echo "✅ Container started with ID: ${CONTAINER_ID:0:12}"

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 5

# Test the health check endpoint
echo "🏥 Testing health check endpoint..."
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/health)

if [ "$HEALTH_CHECK" = "200" ]; then
    echo "✅ Health check endpoint (/health) returns 200 OK"
else
    echo "❌ Health check failed. HTTP status: $HEALTH_CHECK"
fi

# Test the main page
echo "🌐 Testing main page..."
MAIN_PAGE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/)

if [ "$MAIN_PAGE" = "200" ]; then
    echo "✅ Main page (/) returns 200 OK"
else
    echo "❌ Main page failed. HTTP status: $MAIN_PAGE"
fi

# Test health check response content
echo "📄 Health check response content:"
curl -s http://localhost:8082/health
echo ""

# Show nginx logs
echo "📋 Recent nginx logs:"
docker logs --tail 10 $CONTAINER_ID

# Cleanup
echo "🛑 Stopping and removing test container..."
docker stop $CONTAINER_ID > /dev/null
docker rm $CONTAINER_ID > /dev/null

echo ""
echo "🎉 Health check testing completed!"
echo ""
echo "If all tests passed, rebuild and push your image:"
echo "  ./push-to-ecr.sh"
echo ""
echo "Then update your CloudFormation template with the health check fix:"
echo "  Check the file: ecs-health-check-fix.yaml"
