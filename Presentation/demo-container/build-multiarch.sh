#!/bin/bash

# Build script for multi-architecture Docker images
# Supports both x86_64 (amd64) and ARM64 architectures

IMAGE_NAME="demo-container"
TAG="latest"

echo "Building multi-architecture Docker image: $IMAGE_NAME:$TAG"

# Create a new builder instance for multi-platform builds
docker buildx create --name multiarch-builder --use --bootstrap 2>/dev/null || docker buildx use multiarch-builder

# Build for both amd64 and arm64 architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $IMAGE_NAME:$TAG \
  --push \
  .

echo "Multi-architecture build completed!"
echo "Image: $IMAGE_NAME:$TAG"
echo "Platforms: linux/amd64, linux/arm64"
