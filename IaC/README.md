# Nginx Pipeline Setup

This CloudFormation template creates a complete CI/CD pipeline for your nginx container.

## Repository Structure Recommendation

For your use case, I recommend using a **monorepo structure** with folders for different containers:

```
your-repo/
├── nginx/
│   ├── Dockerfile
│   ├── html/
│   │   └── index.html
│   └── conf.d/
│       └── default.conf
├── api/
│   ├── Dockerfile
│   └── src/
└── other-services/
    └── ...
```

## Benefits of Monorepo Structure:
- **Shared dependencies**: Common configuration files, scripts
- **Coordinated deployments**: Deploy related services together
- **Easier maintenance**: Single repository to manage
- **Better visibility**: All code in one place

## How to Deploy

1. **Prerequisites:**
   - GitHub repository with your code
   - GitHub personal access token
   - Existing ECS cluster and service

2. **Deploy the pipeline:**
   ```bash
   aws cloudformation deploy \
     --template-file nginx-pipeline-cf.yaml \
     --stack-name wepl-nginx-pipeline \
     --parameter-overrides \
       GitHubRepo="yourusername/your-repo" \
       GitHubBranch="main" \
       GitHubToken="your-github-token" \
       ContainerPath="nginx" \
       ECSClusterName="your-cluster-name" \
       ECSServiceName="your-service-name" \
     --capabilities CAPABILITY_IAM
   ```

3. **Pipeline Workflow:**
   - Push to your repository triggers the pipeline
   - CodeBuild builds the Docker image from the specified folder
   - Image is pushed to ECR with commit hash tag
   - ECS service is updated with the new image

## Pipeline Features:
- ✅ Automatic builds on git push
- ✅ Docker image building and pushing to ECR
- ✅ Automatic ECS service updates
- ✅ Image versioning with commit hashes
- ✅ ECR lifecycle policy (keeps last 10 images)
- ✅ Secure artifact storage in S3

## Alternative: Separate Repository per Container

If you prefer separate repositories for each container:

**Pros:**
- Independent deployments
- Cleaner access control
- Separate CI/CD pipelines

**Cons:**
- More repositories to manage
- Duplicate configuration
- Harder to coordinate releases

For your project, I recommend the **monorepo approach** since your containers are likely part of the same application ecosystem.
