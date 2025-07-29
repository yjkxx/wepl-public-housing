#!/bin/sh

# Wepl Container Monitoring Script
# This script provides status information about the container services

echo "=== Wepl Container Status ==="
echo "Time: $(date)"
echo

echo "=== Nginx Status ==="
if pgrep nginx > /dev/null; then
    echo "✓ Nginx is running"
    echo "  Processes: $(pgrep nginx | wc -l)"
else
    echo "✗ Nginx is not running"
fi
echo

echo "=== Sync Process Status ==="
if pgrep -f "sync_mainpage" > /dev/null; then
    echo "✓ Background sync process is running"
else
    echo "✗ Background sync process is not running"
fi
echo

echo "=== Directory Status ==="
if [ -d "/usr/share/nginx/html/mainpage" ]; then
    mainpage_files=$(find /usr/share/nginx/html/mainpage -type f | wc -l)
    echo "✓ Mainpage directory exists ($mainpage_files files)"
    if [ -f "/usr/share/nginx/html/mainpage/index.html" ]; then
        echo "  ✓ index.html found"
    else
        echo "  ✗ index.html not found"
    fi
else
    echo "✗ Mainpage directory missing"
fi

if [ -d "/var/cache/nginx/detail" ]; then
    detail_files=$(find /var/cache/nginx/detail -type f -name "*.html" 2>/dev/null | wc -l)
    echo "✓ Detail cache directory exists ($detail_files cached files)"
else
    echo "✗ Detail cache directory missing"
fi
echo

echo "=== Recent Sync Logs ==="
if [ -f "/var/log/wepl/sync.log" ]; then
    echo "Last 5 log entries:"
    tail -5 /var/log/wepl/sync.log | sed 's/^/  /'
else
    echo "No sync log found"
fi
echo

echo "=== Cache Statistics ==="
if [ -d "/var/cache/nginx/proxy_cache" ]; then
    proxy_cache_size=$(du -sh /var/cache/nginx/proxy_cache 2>/dev/null | cut -f1)
    proxy_cache_files=$(find /var/cache/nginx/proxy_cache -type f 2>/dev/null | wc -l)
    echo "Proxy cache: $proxy_cache_size ($proxy_cache_files files)"
else
    echo "Proxy cache directory not found"
fi
echo

echo "=== Disk Usage ==="
df -h /usr/share/nginx/html /var/cache/nginx 2>/dev/null | grep -v Filesystem
echo

echo "=== Memory Usage ==="
free -h 2>/dev/null || echo "Memory info not available"
echo
