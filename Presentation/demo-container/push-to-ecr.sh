#!/bin/bash

# AWS ECR Push Script for Multi-Architecture Images
# This script builds and pushes both x86_64 (amd64) and ARM64 images to ECR

# Configuration
AWS_ACCOUNT_ID="743992917350"
AWS_REGION="ap-northeast-2"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPOSITORY="ecs-pipeline-nginx-743992917350"
IMAGE_TAG="latest"

# Full ECR image URI
ECR_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "🚀 AWS ECR Multi-Architecture Push Script"
echo "=========================================="
echo "Registry: ${ECR_REGISTRY}"
echo "Repository: ${ECR_REPOSITORY}"
echo "Image URI: ${ECR_IMAGE_URI}"
echo ""

# Step 1: Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first:"
    echo "   brew install awscli"
    echo "   or visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

echo "✅ AWS CLI is available"

# Step 2: Check if Docker Buildx is available
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker Buildx is not available. Please update Docker to a newer version."
    exit 1
fi

echo "✅ Docker Buildx is available"

# Step 3: Login to ECR
echo "🔐 Logging in to AWS ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to ECR. Please check your AWS credentials and permissions."
    echo "   Make sure you have configured AWS CLI: aws configure"
    echo "   And have ECR permissions: ecr:GetAuthorizationToken, ecr:BatchCheckLayerAvailability, ecr:GetDownloadUrlForLayer, ecr:BatchGetImage, ecr:InitiateLayerUpload, ecr:UploadLayerPart, ecr:CompleteLayerUpload, ecr:PutImage"
    exit 1
fi

echo "✅ Successfully logged in to ECR"

# Step 4: Create or verify ECR repository exists
echo "📦 Checking if ECR repository exists..."
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${AWS_REGION} &> /dev/null

if [ $? -ne 0 ]; then
    echo "📦 Repository doesn't exist. Creating ECR repository..."
    aws ecr create-repository \
        --repository-name ${ECR_REPOSITORY} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true
    
    if [ $? -eq 0 ]; then
        echo "✅ ECR repository created successfully"
    else
        echo "❌ Failed to create ECR repository. Please check your permissions."
        exit 1
    fi
else
    echo "✅ ECR repository exists"
fi

# Step 5: Create buildx builder for multi-platform builds
echo "🏗️  Setting up multi-platform builder..."
docker buildx create --name ecr-builder --use --bootstrap 2>/dev/null || docker buildx use ecr-builder

# Step 6: Build and push multi-architecture image
echo "🏗️  Building and pushing multi-architecture image..."
echo "   Platforms: linux/amd64, linux/arm64"
echo "   This may take several minutes..."

docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ${ECR_IMAGE_URI} \
    --push \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Successfully built and pushed multi-architecture image!"
    echo "📍 Image URI: ${ECR_IMAGE_URI}"
    echo "🏗️  Supported platforms: linux/amd64, linux/arm64"
    echo ""
    echo "You can now deploy this image using:"
    echo "   docker run -p 8080:80 ${ECR_IMAGE_URI}"
    echo ""
    echo "Or use it in your AWS services (ECS, EKS, etc.) with:"
    echo "   ${ECR_IMAGE_URI}"
else
    echo "❌ Failed to build and push image"
    exit 1
fi

# Cleanup builder (optional)
# docker buildx rm ecr-builder
