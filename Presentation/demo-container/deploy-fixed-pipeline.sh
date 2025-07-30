#!/bin/bash

# Deploy Pipeline with Correct Configuration
# This script deploys the pipeline with the fixed ContainerPath

echo "🚀 Deploying Fixed Pipeline for demo-container"
echo "=============================================="

# Set your parameters here
STACK_NAME="nginx-demo-pipeline"
GITHUB_REPO="yjkxx/wepl-public-housing"  # Update this to your actual repo
GITHUB_BRANCH="test"
ECS_CLUSTER_NAME="ecs-webserver-cluster"
ECS_SERVICE_NAME="ecs-webserver-service"

echo "📋 Configuration:"
echo "   Stack Name: $STACK_NAME"
echo "   GitHub Repo: $GITHUB_REPO"
echo "   GitHub Branch: $GITHUB_BRANCH"
echo "   Container Path: Presentation/demo-container (FIXED!)"
echo "   ECS Cluster: $ECS_CLUSTER_NAME"
echo "   ECS Service: $ECS_SERVICE_NAME"
echo ""

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable not set!"
    echo "   Please set it first:"
    echo "   export GITHUB_TOKEN=your_github_personal_access_token"
    echo ""
    echo "   To create a token: https://github.com/settings/tokens"
    echo "   Required permissions: repo, admin:repo_hook"
    exit 1
fi

echo "✅ GitHub token found"
echo ""

echo "🔧 Deploying CloudFormation stack..."

aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://../../IaC/nginx-pipeline-cf.yaml \
  --parameters \
    ParameterKey=GitHubRepo,ParameterValue="$GITHUB_REPO" \
    ParameterKey=GitHubBranch,ParameterValue="$GITHUB_BRANCH" \
    ParameterKey=GitHubToken,ParameterValue="$GITHUB_TOKEN" \
    ParameterKey=ContainerPath,ParameterValue="Presentation/demo-container" \
    ParameterKey=ECSClusterName,ParameterValue="$ECS_CLUSTER_NAME" \
    ParameterKey=ECSServiceName,ParameterValue="$ECS_SERVICE_NAME" \
    ParameterKey=ImageTag,ParameterValue="latest" \
    ParameterKey=ExistingECRRepository,ParameterValue="ecs-demo-pipeline-nginx-743992917350" \
  --capabilities CAPABILITY_IAM \
  --region ap-northeast-2

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Pipeline deployment initiated!"
    echo ""
    echo "📊 Monitor the deployment:"
    echo "   aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus'"
    echo ""
    echo "🔍 Watch for completion:"
    echo "   aws cloudformation wait stack-create-complete --stack-name $STACK_NAME"
    echo ""
    echo "🎯 Once complete, push a change to trigger the pipeline:"
    echo "   git commit -m 'Test pipeline' --allow-empty"
    echo "   git push origin $GITHUB_BRANCH"
else
    echo ""
    echo "❌ Pipeline deployment failed!"
    echo "   Check the CloudFormation console for details"
fi
