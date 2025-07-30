#!/bin/bash

# 502 Bad Gateway Troubleshooting Script
# This script helps diagnose common causes of 502 errors in ECS

echo "🔍 ECS 502 Bad Gateway Troubleshooting"
echo "======================================"

# Test local container first
echo "1. Testing container locally..."
docker build -t debug-502 . > /dev/null 2>&1
CONTAINER_ID=$(docker run -d -p 8085:80 debug-502)

if [ $? -eq 0 ]; then
    echo "✅ Container started locally"
    sleep 3
    
    # Test health endpoint
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8085/health)
    echo "   Health check: HTTP $HEALTH_STATUS"
    
    # Test debug endpoint
    DEBUG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8085/debug)
    echo "   Debug endpoint: HTTP $DEBUG_STATUS"
    
    # Test main page
    MAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8085/)
    echo "   Main page: HTTP $MAIN_STATUS"
    
    # Get nginx logs
    echo "   Nginx logs:"
    docker logs $CONTAINER_ID 2>&1 | tail -5 | sed 's/^/      /'
    
    docker stop $CONTAINER_ID > /dev/null
    docker rm $CONTAINER_ID > /dev/null
else
    echo "❌ Failed to start container locally"
fi

echo ""
echo "2. Common 502 causes and solutions:"
echo "-----------------------------------"

echo "🔧 LIKELY CAUSES:"
echo ""
echo "A. Container Health Check Issues:"
echo "   - ECS kills containers that fail health checks"
echo "   - ALB gets 502 when routing to dead containers"
echo "   Solution: Check CloudWatch logs for container failures"
echo ""

echo "B. Security Group Issues:"
echo "   - ALB can't reach ECS instances on dynamic ports"
echo "   - Missing port range 32768-65535 in ECS security group"
echo "   Solution: Allow ALB security group to reach ECS dynamic ports"
echo ""

echo "C. Target Group Health Check Path:"
echo "   - Health check path might be wrong in ALB Target Group"
echo "   - Should be '/health' not '/'"
echo "   Solution: Update CloudFormation template"
echo ""

echo "D. Container Resource Limits:"
echo "   - Container runs out of memory/CPU and crashes"
echo "   - ECS kills and restarts containers frequently"
echo "   Solution: Increase memory/CPU allocation"
echo ""

echo "E. File Permissions/Missing Files:"
echo "   - index.html or other files missing from container"
echo "   - Nginx can't read files"
echo "   Solution: Check file copying in Dockerfile"
echo ""

echo "🔍 DEBUGGING COMMANDS:"
echo ""
echo "# Check ECS service status"
echo "aws ecs describe-services --cluster YOUR_CLUSTER --services YOUR_SERVICE"
echo ""

echo "# Check target group health"
echo "aws elbv2 describe-target-health --target-group-arn YOUR_TG_ARN"
echo ""

echo "# Check CloudWatch logs"
echo "aws logs tail /ecs/YOUR_STACK_NAME --follow"
echo ""

echo "# SSH to ECS instance (via bastion) and check:"
echo "docker ps  # See running containers"
echo "docker logs CONTAINER_ID  # Check nginx logs"
echo "curl http://localhost:DYNAMIC_PORT/health  # Test direct container access"
echo ""

echo "🛠️  QUICK FIXES TO TRY:"
echo ""
echo "1. Update health check path in CloudFormation:"
echo "   HealthCheckPath: /health"
echo ""

echo "2. Ensure security group allows ALB to ECS on dynamic ports:"
echo "   FromPort: 32768, ToPort: 65535"
echo ""

echo "3. Check if containers are actually running:"
echo "   ECS Console → Cluster → Service → Tasks"
echo ""

echo "4. Force new deployment:"
echo "   aws ecs update-service --cluster CLUSTER --service SERVICE --force-new-deployment"
echo ""

echo "📊 MONITORING:"
echo ""
echo "- Check ECS service events in AWS Console"
echo "- Monitor CloudWatch metrics for container restart count"
echo "- Check ALB access logs for 502 patterns"
echo "- Review ECS task definition resource allocation"

echo ""
echo "🚀 Next steps:"
echo "1. Push this updated container with better logging: ./push-to-ecr.sh"
echo "2. Update CloudFormation with health check fixes"
echo "3. Monitor CloudWatch logs for detailed error info"
