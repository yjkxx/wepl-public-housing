FROM nginx:alpine

# Install AWS CLI
RUN apk add --no-cache curl unzip python3 py3-pip && \
    pip install awscli && \
    mkdir -p /usr/share/nginx/html/

# Copy your nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Add startup script
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

CMD ["/startup.sh"]
