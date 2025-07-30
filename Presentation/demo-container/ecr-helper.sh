#!/bin/bash

# ECR Helper Script - Common ECR operations

AWS_ACCOUNT_ID="743992917350"
AWS_REGION="ap-northeast-2"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPOSITORY="ecs-pipeline-nginx-743992917350"

case "$1" in
    "login")
        echo "🔐 Logging in to ECR..."
        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
        ;;
    "create-repo")
        echo "📦 Creating ECR repository..."
        aws ecr create-repository \
            --repository-name ${ECR_REPOSITORY} \
            --region ${AWS_REGION} \
            --image-scanning-configuration scanOnPush=true
        ;;
    "list-images")
        echo "📋 Listing images in repository..."
        aws ecr list-images \
            --repository-name ${ECR_REPOSITORY} \
            --region ${AWS_REGION}
        ;;
    "describe-repo")
        echo "📖 Repository information..."
        aws ecr describe-repositories \
            --repository-names ${ECR_REPOSITORY} \
            --region ${AWS_REGION}
        ;;
    "delete-image")
        if [ -z "$2" ]; then
            echo "❌ Please provide image tag: ./ecr-helper.sh delete-image <tag>"
            exit 1
        fi
        echo "🗑️  Deleting image with tag: $2"
        aws ecr batch-delete-image \
            --repository-name ${ECR_REPOSITORY} \
            --region ${AWS_REGION} \
            --image-ids imageTag=$2
        ;;
    "get-uri")
        echo "${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"
        ;;
    *)
        echo "ECR Helper Script"
        echo "Usage: $0 {login|create-repo|list-images|describe-repo|delete-image <tag>|get-uri}"
        echo ""
        echo "Commands:"
        echo "  login          - Login to ECR"
        echo "  create-repo    - Create the ECR repository"
        echo "  list-images    - List all images in the repository"
        echo "  describe-repo  - Show repository information"
        echo "  delete-image   - Delete a specific image tag"
        echo "  get-uri        - Print the full ECR image URI"
        echo ""
        echo "Examples:"
        echo "  $0 login"
        echo "  $0 create-repo"
        echo "  $0 list-images"
        echo "  $0 delete-image latest"
        echo "  $0 get-uri"
        ;;
esac
