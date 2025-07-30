#!/bin/sh

# Enhanced startup script with better error handling
set -e  # Exit on any error

echo "$(date): Container startup initiated..." >> /var/log/wepl/startup.log

# Set up directories
mkdir -p /usr/share/nginx/html/mainpage
mkdir -p /var/cache/nginx/proxy_cache
mkdir -p /var/log/wepl

# Ensure proper permissions
chown -R nginx:nginx /var/cache/nginx
chown -R nginx:nginx /var/log/wepl
chown -R nginx:nginx /usr/share/nginx/html

# Start cron daemon for cache cleanup
crond -b

# Function to sync mainpage from S3
sync_mainpage() {
    echo "$(date): Syncing mainpage from S3..." >> /var/log/wepl/sync.log
    
    # Test S3 access first
    if ! aws s3 ls s3://wepl-mainpage/ > /dev/null 2>&1; then
        echo "$(date): ERROR - Cannot access S3 bucket wepl-mainpage" >> /var/log/wepl/sync.log
        return 1
    fi
    
    aws s3 sync s3://wepl-mainpage /usr/share/nginx/html/mainpage --delete --quiet
    if [ $? -eq 0 ]; then
        echo "$(date): Mainpage sync completed successfully" >> /var/log/wepl/sync.log
        return 0
    else
        echo "$(date): Mainpage sync failed" >> /var/log/wepl/sync.log
        return 1
    fi
}

# Create a fallback index.html in case S3 sync fails
create_fallback_content() {
    echo "$(date): Creating fallback content..." >> /var/log/wepl/startup.log
    cat > /usr/share/nginx/html/mainpage/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>WEPL - Loading...</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        .loading { color: #666; }
        .error { color: #d32f2f; }
    </style>
</head>
<body>
    <h1>WEPL Website</h1>
    <p class="loading">Content is being loaded from S3...</p>
    <p><small>If this message persists, there may be an S3 connectivity issue.</small></p>
</body>
</html>
EOF
}

# Try initial sync with retries
echo "$(date): Starting initial mainpage sync..." >> /var/log/wepl/startup.log
sync_attempts=0
max_attempts=3

while [ $sync_attempts -lt $max_attempts ]; do
    sync_attempts=$((sync_attempts + 1))
    echo "$(date): Sync attempt $sync_attempts of $max_attempts" >> /var/log/wepl/startup.log
    
    if sync_mainpage; then
        echo "$(date): Initial sync successful" >> /var/log/wepl/startup.log
        break
    else
        echo "$(date): Sync attempt $sync_attempts failed" >> /var/log/wepl/startup.log
        if [ $sync_attempts -eq $max_attempts ]; then
            echo "$(date): All sync attempts failed, creating fallback content" >> /var/log/wepl/startup.log
            create_fallback_content
        else
            sleep 5  # Wait before retry
        fi
    fi
done

# Test nginx configuration
echo "$(date): Testing nginx configuration..." >> /var/log/wepl/startup.log
if ! nginx -t; then
    echo "$(date): ERROR - Nginx configuration test failed" >> /var/log/wepl/startup.log
    exit 1
fi

# Start background sync process for mainpage (every 10 minutes)
(
    while true; do
        sleep 600  # 10 minutes
        sync_mainpage
    done
) &

echo "$(date): Background sync process started" >> /var/log/wepl/startup.log

# Ensure health check endpoint works
echo "$(date): Verifying health endpoint..." >> /var/log/wepl/startup.log

# Start nginx
echo "$(date): Starting nginx..." >> /var/log/wepl/startup.log
exec nginx -g "daemon off;"
