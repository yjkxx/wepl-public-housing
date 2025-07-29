FROM nginx:alpine

# Install AWS CLI and other dependencies
RUN apk add --no-cache \
    curl \
    unzip \
    python3 \
    py3-pip \
    bash \
    dcron \
    && pip install awscli \
    && mkdir -p /usr/share/nginx/html/mainpage \
    && mkdir -p /var/cache/nginx/proxy_cache \
    && mkdir -p /var/log/wepl \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/wepl

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY startup.sh /startup.sh

# Make startup script executable
RUN chmod +x /startup.sh

# Add a simple cleanup script for cache management
RUN echo '#!/bin/sh' > /usr/local/bin/cleanup-cache.sh && \
    echo '# Clean up proxy cache files older than 24 hours' >> /usr/local/bin/cleanup-cache.sh && \
    echo 'find /var/cache/nginx/proxy_cache -type f -mtime +1 -delete 2>/dev/null || true' >> /usr/local/bin/cleanup-cache.sh && \
    echo 'echo "$(date): Cache cleanup completed" >> /var/log/wepl/cleanup.log' >> /usr/local/bin/cleanup-cache.sh && \
    chmod +x /usr/local/bin/cleanup-cache.sh

# Add cron job for cache cleanup (runs daily at 2 AM)
RUN echo '0 2 * * * /usr/local/bin/cleanup-cache.sh' > /etc/crontabs/root

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start the application
CMD ["/startup.sh"]
