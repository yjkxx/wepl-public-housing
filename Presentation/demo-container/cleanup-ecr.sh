#!/bin/bash

# Clean up existing ECR repository and redeploy pipeline
echo "🧹 Cleaning up existing ECR repository..."

# Check if repository has images
IMAGES=$(aws ecr list-images --repository-name "ecs-demo-pipeline-nginx-743992917350" --query 'imageIds[].imageTag' --output text 2>/dev/null)

if [ ! -z "$IMAGES" ]; then
    echo "📦 Found images in repository: $IMAGES"
    echo "🗑️  Deleting all images..."
    aws ecr batch-delete-image \
        --repository-name "ecs-demo-pipeline-nginx-743992917350" \
        --image-ids imageTag=latest $(echo $IMAGES | sed 's/[^ ]*/imageTag=&/g') \
        2>/dev/null || echo "Some images may have already been deleted"
fi

echo "🗑️  Deleting ECR repository..."
aws ecr delete-repository --repository-name "ecs-demo-pipeline-nginx-743992917350" --force

echo "✅ Cleanup complete. You can now redeploy the pipeline without the ExistingECRRepository parameter."
