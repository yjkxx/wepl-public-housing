# Use the official nginx base image
FROM nginx:alpine

# Copy custom nginx configuration (optional)
# COPY nginx.conf /etc/nginx/nginx.conf

# Copy static content to nginx html directory
COPY ./html /usr/share/nginx/html

# Copy any custom configuration files
# COPY ./conf.d/*.conf /etc/nginx/conf.d/

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
