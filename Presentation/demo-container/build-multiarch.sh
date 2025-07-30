#!/bin/bash

# Multi-Architecture Container Build Script
# Builds and pushes container images for both ARM64 and x86_64 architectures

set -e

echo "🏗️  Building multi-architecture Docker image: demo-container:latest"
echo "===================================="

# Configuration
ECR_REGISTRY="743992917350.dkr.ecr.ap-northeast-2.amazonaws.com"
ECR_REPOSITORY="ecs-demo-pipeline-nginx-743992917350"
COMMIT_HASH=$(git rev-parse --short HEAD)
IMAGE_NAME="demo-container"

echo "📋 Build Configuration:"
echo "   Registry: $ECR_REGISTRY"
echo "   Repository: $ECR_REPOSITORY"
echo "   Commit Hash: $COMMIT_HASH"
echo "   Architectures: linux/amd64, linux/arm64"
echo ""

# ECR Login
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $ECR_REGISTRY

# Create/use multi-arch builder
echo "🔧 Setting up multi-architecture builder..."
docker buildx create --name multiarch-builder --use --bootstrap 2>/dev/null || docker buildx use multiarch-builder

# Verify builder
echo "🔍 Verifying builder capabilities..."
docker buildx inspect --bootstrap | grep -E "Platforms:|linux/(amd64|arm64)"

# Build and push multi-architecture image
echo ""
echo "🚀 Building and pushing multi-architecture images..."
echo "   Tags:"
echo "     - $ECR_REGISTRY/$ECR_REPOSITORY:latest"
echo "     - $ECR_REGISTRY/$ECR_REPOSITORY:multiarch-$COMMIT_HASH"
echo ""

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $ECR_REGISTRY/$ECR_REPOSITORY:latest \
  --tag $ECR_REGISTRY/$ECR_REPOSITORY:multiarch-$COMMIT_HASH \
  --push \
  .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Multi-architecture build completed successfully!"
    echo ""
    echo "📦 Images built for:"
    echo "   🖥️  linux/amd64 (Intel/AMD x86_64)"
    echo "   💻 linux/arm64 (ARM64/Graviton)"
    echo ""
    echo "🚀 Images pushed to:"
    echo "   $ECR_REGISTRY/$ECR_REPOSITORY:latest"
    echo "   $ECR_REGISTRY/$ECR_REPOSITORY:multiarch-$COMMIT_HASH"
    echo ""
    echo "🎯 Your container will now work on:"
    echo "   ✅ c7g.* instances (ARM64/Graviton)"
    echo "   ✅ c5.*, m5.*, t3.* instances (x86_64)"
    echo "   ✅ Any ECS Fargate (both architectures)"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Update your ECS task definition to use the new image"
    echo "   2. Deploy to ECS service"
    echo "   3. No more 'exec format error'! 🎉"
else
    echo ""
    echo "❌ Build failed!"
    echo "   Check the error messages above"
    exit 1
fi
