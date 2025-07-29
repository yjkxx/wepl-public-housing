#!/bin/bash

# ECS Deployment Script for nginx static website
set -e

# Configuration
STACK_NAME="nginx-website-stack"
REGION="us-east-1"
ECR_REPO_NAME="nginx-website"

echo "🚀 Starting ECS deployment for nginx website..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "📦 Setting up ECR repository..."

# Create ECR repository if it doesn't exist
if ! aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION > /dev/null 2>&1; then
    echo "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION
else
    echo "ECR repository $ECR_REPO_NAME already exists"
fi

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

echo "🏗️  Building Docker image..."
docker build -f nginx.dockerfile -t $ECR_REPO_NAME .

echo "🏷️  Tagging image..."
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest

echo "⬆️  Pushing image to ECR..."
docker push $ECR_URI:latest

echo "☁️  Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file wepl-ecs-cf.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides ContainerImage=$ECR_URI:latest \
    --capabilities CAPABILITY_IAM \
    --region $REGION

echo "📊 Getting stack outputs..."
LOAD_BALANCER_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' --output text)

echo "✅ Deployment complete!"
echo "🌐 Your website is available at: $LOAD_BALANCER_URL"
echo "📈 CloudWatch Dashboard: https://${REGION}.console.aws.amazon.com/cloudwatch/home?region=${REGION}#dashboards:name=nginx-monitoring"

echo ""
echo "💡 Next Steps:"
echo "1. Wait 2-3 minutes for the service to fully start"
echo "2. Test your website at the URL above"
echo "3. Monitor scaling in the CloudWatch dashboard"
echo "4. Consider adding CloudFront for better global performance and caching"

echo ""
echo "💰 Cost Optimization Notes:"
echo "- Using FARGATE_SPOT (70%) + FARGATE (30%) for cost savings"
echo "- Minimum 1 task during low traffic (~$15-20/month)"
echo "- Auto-scales to handle up to 150+ RPS during traffic surges"
echo "- Scales down automatically after traffic reduces"