#!/bin/sh

# Set up directories
mkdir -p /usr/share/nginx/html/mainpage
mkdir -p /var/cache/nginx/proxy_cache
mkdir -p /var/log/wepl

# Start cron daemon for cache cleanup
crond -b

# Function to sync mainpage from S3
sync_mainpage() {
    echo "$(date): Syncing mainpage from S3..." >> /var/log/wepl/sync.log
    aws s3 sync s3://wepl-mainpage /usr/share/nginx/html/mainpage --delete --quiet
    if [ $? -eq 0 ]; then
        echo "$(date): Mainpage sync completed successfully" >> /var/log/wepl/sync.log
    else
        echo "$(date): Mainpage sync failed" >> /var/log/wepl/sync.log
    fi
}

# Initial sync of mainpage
echo "$(date): Starting initial mainpage sync..." >> /var/log/wepl/sync.log
sync_mainpage

# Start background sync process for mainpage (every 10 minutes)
(
    while true; do
        sleep 600  # 10 minutes
        sync_mainpage
    done
) &

echo "$(date): Sync process started in background" >> /var/log/wepl/sync.log

# Start nginx
echo "$(date): Starting nginx..." >> /var/log/wepl/sync.log
nginx -g "daemon off;"
