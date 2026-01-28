# ForestGuard Production Deployment Guide

## Prerequisites

- Ubuntu 22.04 LTS server (Oracle Cloud VM)
- Domain configured: forestguard.freedynamicdns.org
- Ports 80, 443 open in firewall

## Step 1: Install Dependencies

## Step 1: Install Dependencies (Oracle Linux)

```bash
# Update system
sudo dnf update -y

# Enable EPEL and CodeReady Builder (needed for some packages)
sudo dnf install -y oracle-epel-release-el9
sudo dnf config-manager --set-enabled ol9_codeready_builder

# Install Python 3.11 and tools
sudo dnf install -y python3.11 python3.11-devel python3-pip git gcc

# Install Nginx
sudo dnf install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Install Redis
sudo dnf install -y redis
sudo systemctl enable redis
sudo systemctl start redis

# Install Certbot (Let's Encrypt)
sudo dnf install -y certbot python3-certbot-nginx

# Install PostgreSQL client tools
sudo dnf install -y postgresql
```

## Step 2: Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/forestguard
sudo chown opc:opc /opt/forestguard

# Clone repository
cd /opt/forestguard
git clone https://github.com/Nicolasgh91/wildfire-recovery-argentina.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3: Configure Secrets

```bash
# Create secrets directory
sudo mkdir -p /opt/secrets
sudo chown opc:opc /opt/secrets
sudo chmod 700 /opt/secrets

# Copy GEE credentials
# NOTE: Upload gee-service-account.json to server first
cp ~/gee-service-account.json /opt/secrets/
chmod 600 /opt/secrets/gee-service-account.json
```

## Step 4: Generate SECRET_KEY

```bash
# Generate secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Copy output and save for Step 5
```

## Step 5: Configure systemd Service

```bash
# Edit the service file with your actual credentials
nano deployment/forestguard.service

# IMPORTANT: Replace the following placeholders:
# - SECRET_KEY: Use the key generated in Step 4
# - DB_PASSWORD: Your Supabase password
# - SUPABASE_ANON_KEY: From Supabase dashboard
# - SUPABASE_SERVICE_KEY: From Supabase dashboard
# - SUPABASE_JWT_SECRET: From Supabase dashboard
# - FIRMS_API_KEY: Your NASA FIRMS key
# - R2_ACCESS_KEY_ID: Cloudflare R2 key
# - R2_SECRET_ACCESS_KEY: Cloudflare R2 secret

# Copy to systemd directory
sudo cp deployment/forestguard.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/forestguard
sudo chown opc:opc /var/log/forestguard

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable forestguard
sudo systemctl start forestguard

# Check status
sudo systemctl status forestguard
```

## Step 6: Configure Nginx

```bash
# Copy Nginx configuration
sudo cp deployment/nginx.conf /etc/nginx/sites-available/forestguard

# Enable site
sudo ln -s /etc/nginx/sites-available/forestguard /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## Step 7: Setup SSL Certificate

```bash
# Obtain certificate
sudo certbot --nginx -d forestguard.freedynamicdns.org

# Select option 2 (redirect HTTP to HTTPS)
# Certificate will auto-renew

# Test renewal
sudo certbot renew --dry-run
```

## Step 8: Verify Deployment

```bash
# Check API health
curl https://forestguard.freedynamicdns.org/health

# Check API docs
curl https://forestguard.freedynamicdns.org/docs

# View logs
sudo journalctl -u forestguard -f
```

## Step 9: Setup Log Rotation

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/forestguard
```

Add:
```
/var/log/forestguard/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    sharedscripts
    postrotate
        systemctl reload forestguard > /dev/null 2>&1 || true
    endscript
}
```

## Maintenance Commands

### Update Application
```bash
cd /opt/forestguard
git pull origin main
sudo systemctl restart forestguard
```

### View Logs
```bash
# Application logs
sudo journalctl -u forestguard -f

# Nginx access logs
sudo tail -f /var/log/nginx/forestguard_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/forestguard_error.log
```

### Restart Services
```bash
# Restart API
sudo systemctl restart forestguard

# Restart Nginx
sudo systemctl restart nginx

# Restart Redis
sudo systemctl restart redis-server
```

### Check Status
```bash
# All services
sudo systemctl status forestguard nginx redis-server

# API health check
curl https://forestguard.freedynamicdns.org/health

# Database connectivity
psql -h aws-0-us-west-2.pooler.supabase.com -U postgres.qkmuwmxifbahmcydteuj -d postgres -c "SELECT 1;"
```

## Security Checklist

- [ ] SECRET_KEY generated and set
- [ ] All credentials replaced in systemd file
- [ ] GEE credentials in /opt/secrets/ with chmod 600
- [ ] HTTPS enabled with Let's Encrypt
- [ ] Firewall configured (ports 80, 443 only)
- [ ] Log rotation configured
- [ ] Auto-renewal of SSL certificate tested
- [ ] Rate limiting enabled in Nginx
- [ ] Security headers configured
- [ ] DEBUG=false in production

## Troubleshooting

### API not starting
```bash
# Check logs
sudo journalctl -u forestguard -n 50 --no-pager

# Test manually
cd /opt/forestguard
source venv/bin/activate
gunicorn app.main:app --bind 0.0.0.0:8000
```

### SSL certificate issues
```bash
# Renew manually
sudo certbot renew --force-renewal

# Check certificate status
sudo certbot certificates
```

### Database connection issues
```bash
# Test connection
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT version();"

# Check if PostGIS is enabled
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT PostGIS_version();"
```

## Monitoring Setup (Optional)

### UptimeRobot
1. Go to https://uptimerobot.com
2. Add new monitor:
   - Type: HTTPS
   - URL: https://forestguard.freedynamicdns.org/health
   - Interval: 5 minutes

### Sentry (Error Tracking)
```bash
# Add to systemd service file
Environment="SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id"
```

## Backup Strategy

### Database
- Supabase handles automatic backups
- Point-in-time recovery available in Supabase dashboard

### Application Code
- Stored in GitHub repository
- Oracle Cloud VM has daily boot volume backups (free tier)

### Credentials
```bash
# Backup secrets directory (encrypted)
tar czf secrets-backup-$(date +%Y%m%d).tar.gz /opt/secrets/
gpg -c secrets-backup-*.tar.gz
rm secrets-backup-*.tar.gz
# Store .gpg file securely offline
```
