#!/bin/bash

# Simple ECR Push Script (single architecture - current platform)
# Use this for faster builds when you don't need multi-architecture support

# Configuration
AWS_ACCOUNT_ID="743992917350"
AWS_REGION="ap-northeast-2"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPOSITORY="ecs-pipeline-nginx-743992917350"
IMAGE_TAG="latest"

# Full ECR image URI
ECR_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "🚀 AWS ECR Simple Push Script (Single Architecture)"
echo "==================================================="
echo "Image URI: ${ECR_IMAGE_URI}"
echo ""

# Login to ECR
echo "🔐 Logging in to AWS ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to ECR"
    exit 1
fi

# Build image locally
echo "🏗️  Building Docker image..."
docker build -t ${ECR_IMAGE_URI} .

if [ $? -ne 0 ]; then
    echo "❌ Failed to build image"
    exit 1
fi

# Push image
echo "📤 Pushing image to ECR..."
docker push ${ECR_IMAGE_URI}

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Successfully pushed image!"
    echo "📍 Image URI: ${ECR_IMAGE_URI}"
else
    echo "❌ Failed to push image"
    exit 1
fi
