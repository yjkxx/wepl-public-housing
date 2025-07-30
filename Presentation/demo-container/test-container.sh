#!/bin/bash

# Test script to verify the container works correctly

echo "🐳 Testing Demo Container Setup"
echo "================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Build the image
echo "📦 Building Docker image..."
if docker build -t demo-container . > /dev/null 2>&1; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

# Test run the container
echo "🚀 Testing container..."
CONTAINER_ID=$(docker run -d -p 8081:80 demo-container)

if [ $? -eq 0 ]; then
    echo "✅ Container started successfully"
    echo "🌐 Website should be available at: http://localhost:8081"
    
    # Wait a moment for the container to fully start
    sleep 3
    
    # Test if the website is accessible
    if curl -s http://localhost:8081 > /dev/null; then
        echo "✅ Website is accessible"
    else
        echo "⚠️  Website might not be ready yet, try accessing http://localhost:8081 manually"
    fi
    
    echo ""
    echo "🛑 Stopping test container..."
    docker stop $CONTAINER_ID > /dev/null
    docker rm $CONTAINER_ID > /dev/null
    echo "✅ Test completed successfully"
else
    echo "❌ Failed to start container"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Your container is ready to use."
echo ""
echo "To run the container:"
echo "  docker-compose up --build"
echo "  or"
echo "  docker run -d -p 8080:80 --name demo-container demo-container"
