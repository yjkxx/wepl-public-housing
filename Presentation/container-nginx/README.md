# Wepl Nginx Container Setup

This container provides a hybrid content delivery solution that combines local mainpage serving with on-demand detail page caching from S3.

## Features

### Mainpage Serving
- **Initial Sync**: Downloads all files from `wepl-mainpage` S3 bucket on container start
- **Periodic Sync**: Automatically syncs every 10 minutes to keep mainpage content up-to-date
- **Local Serving**: Serves mainpage files directly from local storage for optimal performance

### Detail Page Caching
- **On-Demand Fetching**: Downloads detail pages from `wepl-posting-pages` S3 bucket only when requested
- **Local Caching**: Stores fetched pages locally for 1 hour to improve subsequent access times
- **Automatic Cleanup**: Removes old cache files daily to manage disk space

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │    │   Nginx          │    │   AWS S3        │
│   Requests      │───▶│   Container      │───▶│   Buckets       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Local Cache    │
                       │   & Storage      │
                       └──────────────────┘
```

## File Structure

- `Dockerfile` - Container build configuration
- `nginx.conf` - Nginx server configuration
- `startup.sh` - Container initialization and sync management
- `buildspec.yml` - AWS CodeBuild specification for CI/CD pipeline
- `monitor.sh` - Status monitoring script

## Building and Running

### Build the Container
```bash
docker build -t wepl-nginx .
```

### Run the Container
```bash
docker run -d \
  --name wepl-nginx \
  -p 80:80 \
  -e AWS_ACCESS_KEY_ID=your_access_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret_key \
  -e AWS_DEFAULT_REGION=ap-northeast-2 \
  wepl-nginx
```

### With Docker Compose
```yaml
version: '3.8'
services:
  nginx:
    build:
      context: .
      dockerfile: nginx.dockerfile
    ports:
      - "80:80"
    environment:
      - AWS_ACCESS_KEY_ID=your_access_key
      - AWS_SECRET_ACCESS_KEY=your_secret_key
      - AWS_DEFAULT_REGION=ap-northeast-2
    volumes:
      - nginx_cache:/var/cache/nginx
      - nginx_logs:/var/log/wepl
    restart: unless-stopped

volumes:
  nginx_cache:
  nginx_logs:
```

## Endpoints

### Main Endpoints
- `/` - Mainpage content (served locally, synced from `wepl-mainpage`)
- `/detail/*` - Detail pages (cached on-demand from `wepl-posting-pages`)
- `/legacy/*` - Legacy content (proxied to S3 website)

### Monitoring Endpoints
- `/health` - Health check endpoint
- `/cache-status` - Cache status information

## Monitoring

### Check Container Status
```bash
# Execute monitoring script inside container
docker exec wepl-nginx /bin/sh /monitor.sh

# Check logs
docker logs wepl-nginx

# Check sync logs
docker exec wepl-nginx tail -f /var/log/wepl/sync.log
```

### Manual Operations
```bash
# Force mainpage sync
docker exec wepl-nginx aws s3 sync s3://wepl-mainpage /usr/share/nginx/html/mainpage --delete

# Clear detail cache
docker exec wepl-nginx rm -rf /var/cache/nginx/detail/*

# Check cache size
docker exec wepl-nginx du -sh /var/cache/nginx/
```

## Configuration

### Environment Variables
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key  
- `AWS_DEFAULT_REGION` - AWS region (default: ap-northeast-2)

### Customization
- **Sync Interval**: Modify the `sleep 600` value in `startup.sh` (600 = 10 minutes)
- **Cache TTL**: Adjust cache expiration times in `nginx.conf`
- **S3 Buckets**: Update bucket names in configuration files

## Troubleshooting

### Common Issues
1. **AWS Credentials**: Ensure proper AWS credentials are set
2. **S3 Permissions**: Verify read access to both S3 buckets
3. **Network**: Check connectivity to S3 endpoints
4. **Disk Space**: Monitor cache directory sizes

### Debug Commands
```bash
# Check AWS CLI configuration
docker exec wepl-nginx aws sts get-caller-identity

# Test S3 access
docker exec wepl-nginx aws s3 ls s3://wepl-mainpage
docker exec wepl-nginx aws s3 ls s3://wepl-posting-pages

# Check nginx configuration
docker exec wepl-nginx nginx -t
```

## Performance Considerations

- **Memory**: Container uses minimal memory for caching
- **Storage**: Cache grows based on accessed detail pages
- **Network**: Reduced S3 requests due to local caching
- **Latency**: Mainpage served locally, detail pages cached after first request

## Security Notes

- Use IAM roles instead of access keys when possible
- Limit S3 bucket permissions to read-only
- Consider using VPC endpoints for S3 access
- Regularly update container base images
