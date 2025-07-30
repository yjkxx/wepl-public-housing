# 한눈에 공공임대 - Docker Container

This repository contains a Korean public housing information website that can be containerized with nginx for both x86 and ARM architectures.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up --build

# Access the website at http://localhost:8080
```

### Using Docker directly

```bash
# Build the image
docker build -t demo-container .

# Run the container
docker run -d -p 8080:80 --name demo-container demo-container

# Access the website at http://localhost:8080
```

## Multi-Architecture Support

This container supports both x86_64 (amd64) and ARM64 architectures.

### Building for Multiple Architectures

1. **Enable Docker BuildKit** (if not already enabled):
   ```bash
   export DOCKER_BUILDKIT=1
   ```

2. **Use the provided build script**:
   ```bash
   ./build-multiarch.sh
   ```

3. **Manual multi-architecture build**:
   ```bash
   # Create builder
   docker buildx create --name multiarch-builder --use --bootstrap
   
   # Build for multiple platforms
   docker buildx build --platform linux/amd64,linux/arm64 -t demo-container:latest --push .
   ```

## Architecture

- **Base Image**: `nginx:alpine` (lightweight, secure)
- **Web Server**: Nginx with custom configuration
- **Content**: Static HTML, CSS, JavaScript files
- **Port**: 80 (mapped to 8080 in docker-compose)

## Files Structure

- `index.html` - Main landing page
- `HUG-*.html` - HUG housing detail pages
- `LH-*.html` - LH housing detail pages  
- `SH-*.html` - SH housing detail pages
- `style.css` - Custom styles
- `script.js` - JavaScript functionality
- `logo.png` - Logo image
- `nginx.conf` - Custom nginx configuration

## Configuration

The nginx configuration includes:
- Gzip compression for better performance
- Security headers
- Static file caching
- Error page handling
- Support for single-page application routing

## Development

To make changes to the website:

1. Edit the HTML, CSS, or JS files
2. Rebuild the container:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

## Production Deployment

### AWS ECR Deployment

#### Prerequisites
- AWS CLI installed and configured (`aws configure`)
- Docker with Buildx support
- ECR permissions (GetAuthorizationToken, BatchCheckLayerAvailability, etc.)

#### Multi-Architecture Push (Recommended)
```bash
# Push to ECR with both x86_64 and ARM64 support
./push-to-ecr.sh
```

#### Simple Push (Single Architecture)
```bash
# Faster build for current platform only
./push-to-ecr-simple.sh
```

#### ECR Helper Commands
```bash
# Login to ECR
./ecr-helper.sh login

# Create repository (if it doesn't exist)
./ecr-helper.sh create-repo

# List images in repository
./ecr-helper.sh list-images

# Get the full ECR URI
./ecr-helper.sh get-uri
```

#### Manual ECR Push
If you prefer manual steps:
```bash
# 1. Login to ECR
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 743992917350.dkr.ecr.ap-northeast-2.amazonaws.com

# 2. Build and tag image
docker build -t 743992917350.dkr.ecr.ap-northeast-2.amazonaws.com/wepl/webserver:latest .

# 3. Push image
docker push 743992917350.dkr.ecr.ap-northeast-2.amazonaws.com/wepl/webserver:latest
```

### Other Production Considerations

For production deployment:

1. Update the `docker-compose.yml` file with appropriate environment variables
2. Consider using a reverse proxy (nginx, traefik) for SSL termination
3. Set up proper logging and monitoring
4. Use specific version tags instead of `latest`

## Troubleshooting

### Container won't start
- Check if port 8080 is already in use: `lsof -i :8080`
- View container logs: `docker-compose logs`

### Website not loading
- Ensure all files are copied correctly
- Check nginx configuration syntax: `docker exec demo-container nginx -t`

### Multi-arch build issues
- Ensure Docker BuildKit is enabled
- Check if buildx is installed: `docker buildx version`
