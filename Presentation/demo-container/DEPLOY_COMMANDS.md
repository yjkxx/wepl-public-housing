# Manual Pipeline Deployment Commands
# Copy and paste these commands to deploy your fixed pipeline

# 1. Set your GitHub token (replace with your actual token)
export GITHUB_TOKEN="your_github_personal_access_token_here"

# 2. Deploy the pipeline with correct ContainerPath and existing ECR repository
aws cloudformation create-stack \
  --stack-name "nginx-demo-pipeline" \
  --template-body file://../../IaC/nginx-pipeline-cf.yaml \
  --parameters \
    ParameterKey=GitHubRepo,ParameterValue="yjkxx/wepl-public-housing" \
    ParameterKey=GitHubBranch,ParameterValue="test" \
    ParameterKey=GitHubToken,ParameterValue="$GITHUB_TOKEN" \
    ParameterKey=ContainerPath,ParameterValue="Presentation/demo-container" \
    ParameterKey=ECSClusterName,ParameterValue="ecs-webserver-cluster" \
    ParameterKey=ECSServiceName,ParameterValue="ecs-webserver-service" \
    ParameterKey=ImageTag,ParameterValue="latest" \
    ParameterKey=ExistingECRRepository,ParameterValue="ecs-demo-pipeline-nginx-743992917350" \
  --capabilities CAPABILITY_IAM \
  --region ap-northeast-2

# 3. Wait for completion
aws cloudformation wait stack-create-complete --stack-name "nginx-demo-pipeline"

# 4. Check status
aws cloudformation describe-stacks --stack-name "nginx-demo-pipeline" --query 'Stacks[0].StackStatus'

# 5. Trigger pipeline with a test commit
git commit -m 'Test fixed pipeline' --allow-empty
git push origin test
