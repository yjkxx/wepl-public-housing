#!/bin/bash

# Debug script to check ECS deployment status and logs

echo "=== ECS Deployment Debug Script ==="
echo "Date: $(date)"
echo

# Set your stack name here
STACK_NAME="${1:-wepl-ecs-02}"
AWS_REGION="${AWS_DEFAULT_REGION:-ap-northeast-2}"

echo "Using Stack Name: $STACK_NAME"
echo "Using Region: $AWS_REGION"
echo

# Check ECS Cluster
echo "=== ECS Cluster Status ==="
aws ecs describe-clusters --clusters "${STACK_NAME}-cluster" --region $AWS_REGION --query 'clusters[0].{Status:status,RunningTasks:runningTasksCount,ActiveServices:activeServicesCount}' || echo "Cluster not found"
echo

# Check ECS Service
echo "=== ECS Service Status ==="
aws ecs describe-services --cluster "${STACK_NAME}-cluster" --services "${STACK_NAME}-service" --region $AWS_REGION --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount,TaskDefinition:taskDefinition}' || echo "Service not found"
echo

# Check running tasks
echo "=== Running Tasks ==="
TASK_ARNS=$(aws ecs list-tasks --cluster "${STACK_NAME}-cluster" --service-name "${STACK_NAME}-service" --region $AWS_REGION --query 'taskArns' --output text 2>/dev/null)

if [ -n "$TASK_ARNS" ] && [ "$TASK_ARNS" != "None" ]; then
    for TASK_ARN in $TASK_ARNS; do
        echo "Task: $(basename $TASK_ARN)"
        aws ecs describe-tasks --cluster "${STACK_NAME}-cluster" --tasks $TASK_ARN --region $AWS_REGION --query 'tasks[0].{LastStatus:lastStatus,HealthStatus:healthStatus,CreatedAt:createdAt,StoppedReason:stoppedReason}' 2>/dev/null
        echo
    done
else
    echo "No running tasks found"
    
    # Check stopped tasks for debugging
    echo "=== Recent Stopped Tasks ==="
    STOPPED_TASKS=$(aws ecs list-tasks --cluster "${STACK_NAME}-cluster" --desired-status STOPPED --region $AWS_REGION --query 'taskArns[0:3]' --output text 2>/dev/null)
    if [ -n "$STOPPED_TASKS" ] && [ "$STOPPED_TASKS" != "None" ]; then
        for TASK_ARN in $STOPPED_TASKS; do
            echo "Stopped Task: $(basename $TASK_ARN)"
            aws ecs describe-tasks --cluster "${STACK_NAME}-cluster" --tasks $TASK_ARN --region $AWS_REGION --query 'tasks[0].{LastStatus:lastStatus,StoppedReason:stoppedReason,StoppedAt:stoppedAt}' 2>/dev/null
            echo
        done
    fi
fi

# Check ALB Target Group Health
echo "=== Target Group Health ==="
TG_ARN=$(aws elbv2 describe-target-groups --names "${STACK_NAME}-tg" --region $AWS_REGION --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)
if [ "$TG_ARN" != "None" ] && [ -n "$TG_ARN" ]; then
    aws elbv2 describe-target-health --target-group-arn $TG_ARN --region $AWS_REGION --query 'TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State,Reason:TargetHealth.Reason,Description:TargetHealth.Description}' 2>/dev/null
else
    echo "Target group not found"
fi
echo

# Get ALB DNS
echo "=== Load Balancer DNS ==="
ALB_DNS=$(aws elbv2 describe-load-balancers --names "${STACK_NAME}-alb" --region $AWS_REGION --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null)
if [ "$ALB_DNS" != "None" ] && [ -n "$ALB_DNS" ]; then
    echo "ALB DNS: $ALB_DNS"
    echo "Health Check URL: http://$ALB_DNS/health"
    echo "Test with: curl -v http://$ALB_DNS/health"
else
    echo "Load balancer not found"
fi
echo

# Check Auto Scaling Groups
echo "=== Auto Scaling Groups ==="
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "${STACK_NAME}-ecs-spot-asg" --region $AWS_REGION --query 'AutoScalingGroups[0].{GroupName:AutoScalingGroupName,Desired:DesiredCapacity,Min:MinSize,Max:MaxSize,Instances:length(Instances)}' 2>/dev/null || echo "Spot ASG not found"

aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "${STACK_NAME}-ecs-ondemand-asg" --region $AWS_REGION --query 'AutoScalingGroups[0].{GroupName:AutoScalingGroupName,Desired:DesiredCapacity,Min:MinSize,Max:MaxSize,Instances:length(Instances)}' 2>/dev/null || echo "OnDemand ASG not found"
echo

# Check recent CloudWatch logs
echo "=== Recent CloudWatch Logs ==="
LOG_GROUP="/ecs/${STACK_NAME}"
echo "Log Group: $LOG_GROUP"
RECENT_STREAMS=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --region $AWS_REGION --order-by LastEventTime --descending --max-items 3 --query 'logStreams[*].logStreamName' --output text 2>/dev/null)

if [ -n "$RECENT_STREAMS" ] && [ "$RECENT_STREAMS" != "None" ]; then
    echo "Recent log streams: $RECENT_STREAMS"
    
    # Get recent log events from the most recent stream
    LATEST_STREAM=$(echo $RECENT_STREAMS | awk '{print $1}')
    echo
    echo "=== Recent Log Events from $LATEST_STREAM ==="
    aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name "$LATEST_STREAM" --region $AWS_REGION --limit 10 --query 'events[*].message' --output text 2>/dev/null | tail -10
else
    echo "No log streams found or log group doesn't exist"
fi
echo

echo "=== Debug Complete ==="
echo
echo "Next Steps:"
echo "1. Check the ALB DNS name above and test the health endpoint"
echo "2. Verify target group shows healthy targets"
echo "3. Check CloudWatch logs for container errors"
echo "4. Verify S3 bucket permissions (wepl-mainpage, wepl-posting-pages)"
echo "5. Check if ECS instances are running in the ASG"
