# Production Deployment Guide

This guide provides step-by-step instructions for deploying the crypto trading platform backend to production.

## Prerequisites

### System Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ recommended
- **Storage**: 100GB+ SSD
- **OS**: Ubuntu 20.04+ or CentOS 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### External Services
- **Domain name** (for SSL certificates)
- **SSL certificates** (Let's Encrypt recommended)
- **Email service** (SMTP server)
- **Monitoring service** (optional, e.g., Sentry)

## Pre-Deployment Checklist

### 1. Security Configuration
- [ ] Generate strong `SECRET_KEY`
- [ ] Set up secure database password
- [ ] Configure SSL certificates
- [ ] Set up firewall rules
- [ ] Configure backup strategy

### 2. Environment Setup
- [ ] Copy `.env.docker` to `.env`
- [ ] Fill in all required environment variables
- [ ] Verify domain DNS settings
- [ ] Set up email configuration

### 3. Infrastructure Preparation
- [ ] Install Docker and Docker Compose
- [ ] Configure system firewall
- [ ] Set up log rotation
- [ ] Configure monitoring

## Deployment Steps

### 1. Clone and Prepare Repository

```bash
# Clone the repository
git clone <your-repo-url>
cd crypto-platform

# Copy environment template
cp .env.docker .env

# Edit environment variables
nano .env
```

### 2. Configure Environment Variables

Edit `.env` file with your production values:

```bash
# Security
SECRET_KEY=your-super-secret-key-here-change-in-production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database
DB_PASSWORD=your-secure-db-password-generate-random-one

# Email (optional but recommended)
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn-if-using-sentry
```

### 3. Deploy the Application

```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy the application
./deploy.sh deploy
```

The deployment script will:
- Build Docker images
- Start all services (web, database, redis, nginx, celery)
- Run database migrations
- Collect static files
- Create admin user
- Load initial data

### 4. Verify Deployment

Check that all services are running:

```bash
./deploy.sh status
```

Test the application:

```bash
# Health check
curl http://localhost/health/

# API documentation
curl http://localhost/api/docs/

# Admin panel
# Open http://localhost/admin in browser
```

## SSL/HTTPS Configuration

### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 2: Custom Certificates

1. Place certificates in `/etc/ssl/certs/`
2. Update `docker/nginx/nginx.conf` with certificate paths
3. Uncomment SSL configuration in nginx.conf

## Post-Deployment Configuration

### 1. Create Initial Trading Pairs

Access the admin panel and create trading pairs:

1. Go to http://localhost/admin
2. Login with admin credentials
3. Navigate to "Trading pairs"
4. Add pairs like:
   - BTC/USD
   - ETH/USD
   - LTC/USD

### 2. Configure External APIs

Add API keys for external services:

```bash
# Edit .env file
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key
COINGECKO_API_KEY=your-coingecko-api-key

# Restart services
./deploy.sh restart
```

### 3. Set Up Monitoring

Access monitoring dashboards:
- **Application health**: http://localhost/health/
- **Celery tasks**: http://localhost:5555
- **System metrics**: http://localhost/metrics/

## Maintenance Operations

### Daily Tasks

```bash
# Check service status
./deploy.sh status

# View logs
./deploy.sh logs

# Check health
curl http://localhost/health/
```

### Weekly Tasks

```bash
# Create database backup
./deploy.sh backup

# Update application
./deploy.sh update

# Check for security updates
docker-compose pull
```

### Monthly Tasks

```bash
# Clean up old Docker images
docker system prune -f

# Review logs for issues
./deploy.sh logs web | grep ERROR

# Update SSL certificates (if not auto-renewing)
sudo certbot renew
```

## Backup and Recovery

### Automated Backups

Set up cron jobs for automated backups:

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/crypto-platform/deploy.sh backup

# Add weekly backup verification
0 3 * * 0 /path/to/crypto-platform/scripts/verify_backups.sh
```

### Manual Backup

```bash
# Create backup
./deploy.sh backup

# List backup files
ls -la backup_*.sql

# Restore from backup
./deploy.sh restore backup_20231201_020000.sql
```

## Scaling and Performance

### Horizontal Scaling

To scale the web application:

```bash
# Edit docker-compose.yml
# Increase web service replicas:
services:
  web:
    replicas: 3  # Increase from 1

# Redeploy
docker-compose up -d --scale web=3
```

### Database Scaling

For high-traffic deployments:
- Consider read replicas
- Use connection pooling
- Implement database sharding

### Caching Optimization

Monitor Redis usage and optimize:
```bash
# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Monitor cache hit rate
docker-compose exec redis redis-cli info stats
```

## Security Hardening

### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Database from outside
sudo ufw deny 6379/tcp  # Redis from outside
```

### Security Headers

The application already includes security headers. Verify they're working:

```bash
curl -I http://localhost
```

Look for headers like:
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Strict-Transport-Security (HTTPS)

### Regular Security Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Docker images
docker-compose pull
docker-compose up -d

# Check for vulnerabilities
docker scan crypto-platform_web
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
./deploy.sh logs web

# Check configuration
docker-compose config

# Restart services
./deploy.sh restart
```

#### Database Connection Issues
```bash
# Check database status
docker-compose exec db pg_isready -U crypto_user

# Check database logs
./deploy.sh logs db

# Reset database (last resort)
docker-compose down -v
docker-compose up -d db
./deploy.sh deploy
```

#### High Memory Usage
```bash
# Check memory usage
docker stats

# Restart services
./deploy.sh restart

# Check for memory leaks
./deploy.sh logs web | grep -i memory
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test SSL configuration
openssl s_client -connect yourdomain.com:443
```

### Performance Issues

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/health/

# Monitor system resources
docker stats

# Check slow queries
docker-compose exec db psql -U crypto_user -d crypto_platform -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

## Emergency Procedures

### Service Outage

1. **Check health status**
   ```bash
   curl http://localhost/health/
   ./deploy.sh status
   ```

2. **Review logs**
   ```bash
   ./deploy.sh logs
   ```

3. **Restart services**
   ```bash
   ./deploy.sh restart
   ```

4. **Restore from backup** (if needed)
   ```bash
   ./deploy.sh restore latest_backup.sql
   ```

### Security Incident

1. **Isolate affected services**
   ```bash
   docker-compose stop web
   ```

2. **Review logs**
   ```bash
   ./deploy.sh logs | grep -i "security\|attack\|breach"
   ```

3. **Change credentials**
   - Update database password
   - Rotate API keys
   - Change SECRET_KEY

4. **Restore from clean backup**
   ```bash
   ./deploy.sh restore pre-incident_backup.sql
   ```

## Support and Monitoring

### Health Monitoring

Set up monitoring for:
- HTTP health checks
- Database connectivity
- Redis connectivity
- Disk space usage
- Memory usage
- Error rates

### Alerting

Configure alerts for:
- Service downtime
- High error rates
- Low disk space
- High memory usage
- Failed authentication attempts

### Log Analysis

Regularly review logs for:
- Error patterns
- Security events
- Performance issues
- User activity patterns

## Contact Information

For support:
- **Technical issues**: Create GitHub issue
- **Security incidents**: security@yourdomain.com
- **Emergency support**: +1-XXX-XXX-XXXX

---

**Note**: This guide should be customized based on your specific infrastructure and security requirements. Always test deployment procedures in a staging environment before applying to production.
