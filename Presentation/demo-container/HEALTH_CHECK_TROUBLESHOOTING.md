# ECS Health Check Troubleshooting Guide

## 🏥 Common ECS Health Check Issues and Solutions

### 1. **Health Check Endpoint Issue** ✅ FIXED
**Problem**: ECS health checks failing because no dedicated health endpoint exists.
**Solution**: Added `/health` endpoint that returns 200 OK.

### 2. **IPv6 Listener Issue** ✅ FIXED  
**Problem**: `listen [::]:80` can cause issues in some ECS configurations.
**Solution**: Removed IPv6 listener, using only `listen 80`.

### 3. **CloudFormation Health Check Configuration**
Update your CloudFormation template with these changes:

```yaml
# In ALBTargetGroup section:
HealthCheckPath: /health                    # Changed from /
HealthCheckTimeoutSeconds: 5               # Reduced from 10
UnhealthyThresholdCount: 3                 # Reduced from 5

# In ECS Task Definition, add container health check:
HealthCheck:
  Command:
    - CMD-SHELL
    - 'curl -f http://localhost/health || exit 1'
  Interval: 30
  Timeout: 5
  Retries: 3
  StartPeriod: 60                          # Give container time to start
```

### 4. **Container Startup Time**
- Added `StartPeriod: 60` to give container 60 seconds to fully start
- ECS will wait before starting health checks

### 5. **Testing Health Checks**

#### Local Testing:
```bash
# Test the health check fix
./test-health-check.sh
```

#### Manual Testing:
```bash
# Build and run locally
docker build -t test-container .
docker run -d -p 8080:80 test-container

# Test health endpoint
curl http://localhost:8080/health    # Should return "healthy"
curl -I http://localhost:8080/       # Should return 200 OK
```

### 6. **ECS Service Logs**
Check your CloudWatch logs at: `/ecs/your-stack-name`

Common error patterns to look for:
- `nginx: [emerg]` - Configuration errors
- `connect() failed` - Network connectivity issues
- `404` errors - Missing files or incorrect paths

### 7. **Deployment Steps**

1. **Test locally first**:
   ```bash
   ./test-health-check.sh
   ```

2. **Push updated image to ECR**:
   ```bash
   ./push-to-ecr.sh
   ```

3. **Update CloudFormation template** with the health check fixes from `ecs-health-check-fix.yaml`

4. **Deploy the stack update**:
   ```bash
   aws cloudformation update-stack \
     --stack-name your-stack-name \
     --template-body file://wepl-ecs-02-cf.yaml \
     --parameters ParameterKey=KeyPairName,ParameterValue=your-key-pair \
     --capabilities CAPABILITY_IAM
   ```

5. **Force new deployment** (if needed):
   ```bash
   aws ecs update-service \
     --cluster your-cluster-name \
     --service your-service-name \
     --force-new-deployment
   ```

### 8. **Monitoring Health**

#### Check ECS Service Health:
```bash
aws ecs describe-services \
  --cluster your-cluster-name \
  --services your-service-name
```

#### Check Target Group Health:
```bash
aws elbv2 describe-target-health \
  --target-group-arn your-target-group-arn
```

### 9. **Quick Fixes if Still Failing**

If health checks still fail after these changes:

1. **Simplify health check** - Change path back to `/` temporarily
2. **Increase timeouts** - Set `HealthCheckTimeoutSeconds: 10`
3. **Check security groups** - Ensure port 80 is open from ALB to ECS instances
4. **Verify image** - Make sure the latest image is being pulled

### 10. **Debug Commands**

Connect to your ECS instance via bastion host and check:
```bash
# Check if containers are running
docker ps

# Check container logs
docker logs <container-id>

# Test health check from inside the instance
curl http://localhost:<dynamic-port>/health
```

## 🚀 Next Steps

1. Run `./test-health-check.sh` to verify fixes work locally
2. Push updated image: `./push-to-ecr.sh`
3. Update CloudFormation template with health check fixes
4. Deploy and monitor the service

The main fixes are:
- ✅ Added dedicated `/health` endpoint
- ✅ Removed IPv6 listener  
- ✅ Optimized health check timing
- ✅ Added container-level health checks
