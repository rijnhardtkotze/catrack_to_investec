# Car Service Savings Admin UI - Deployment Guide

## Overview

This guide covers deploying the management admin UI for your car service savings Lambda function. The admin UI provides comprehensive CRUD operations, error logging, and investigation tools.

## What's Been Created

### 📁 Admin UI Structure
```
admin_ui/
├── app.py                 # Main Flask application
├── run.py                 # Production runner
├── requirements.txt       # Python dependencies
├── setup.sh              # Automated setup script
├── README.md             # Comprehensive documentation
├── .env.example          # Environment configuration template
└── templates/            # HTML templates
    ├── base.html         # Base template with navigation
    ├── dashboard.html    # Main dashboard with metrics
    ├── config_list.html  # Configuration management
    ├── config_form.html  # Configuration create/edit
    ├── transaction_list.html   # Transaction history
    ├── transaction_detail.html # Transaction details
    ├── error_list.html   # Error log management
    ├── error_detail.html # Error investigation
    └── test_page.html    # Testing and debugging tools
```

### 🚀 Enhanced Lambda Function
The original `service.py` has been enhanced with:
- **Structured logging** with multiple severity levels
- **Error tracking** with stack traces and context
- **Transaction logging** for all operations
- **DynamoDB integration** for persistent logging
- **Better error handling** with graceful failures
- **Configuration validation** and missing parameter detection

## Deployment Options

### Option 1: Local Development
```bash
cd admin_ui
./setup.sh
python3 run.py
```
Access at: http://localhost:5000

### Option 2: AWS EC2 Instance
1. **Launch EC2 instance** (t3.micro is sufficient)
2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```
3. **Clone and setup**:
   ```bash
   git clone your-repo
   cd admin_ui
   ./setup.sh
   ```
4. **Configure Nginx** (see nginx config below)
5. **Run with Gunicorn**:
   ```bash
   gunicorn -w 4 -b 127.0.0.1:5000 app:app
   ```

### Option 3: AWS Fargate (Container)
1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 5000
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
   ```
2. **Build and push to ECR**
3. **Deploy using Fargate**

### Option 4: AWS Elastic Beanstalk
1. **Zip the admin_ui directory**
2. **Create new Elastic Beanstalk application**
3. **Upload and deploy**

## Configuration Setup

### 1. AWS Credentials
```bash
# Option A: AWS CLI
aws configure

# Option B: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=eu-west-1

# Option C: IAM Role (recommended for EC2/Fargate)
```

### 2. Environment Configuration
Copy and edit the environment file:
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 3. Database Setup
The setup script automatically creates the SQLite database with:
- **Configuration table** for settings management
- **Transaction log table** for operation history  
- **Error log table** for detailed error tracking

### 4. AWS Permissions
Ensure your AWS credentials have these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunction",
                "lambda:UpdateFunctionConfiguration",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams", 
                "logs:GetLogEvents",
                "cloudwatch:GetMetricStatistics",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "*"
        }
    ]
}
```

## Production Configuration

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/admin_ui/static;
        expires 1d;
    }
}
```

### SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Systemd Service (Linux)
Create `/etc/systemd/system/car-admin.service`:
```ini
[Unit]
Description=Car Service Admin UI
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/admin_ui
Environment=PATH=/path/to/admin_ui/venv/bin
ExecStart=/path/to/admin_ui/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable car-admin
sudo systemctl start car-admin
```

## Security Considerations

### 1. Environment Variables
- **Never commit** `.env` files to version control
- **Use AWS Secrets Manager** for production credentials
- **Rotate secrets** regularly

### 2. Network Security
- **Use HTTPS** in production (SSL certificate)
- **Restrict access** with VPC security groups
- **Enable CloudTrail** for audit logging

### 3. Database Security
- **Upgrade to PostgreSQL** for production (better security)
- **Enable encryption** at rest and in transit
- **Regular backups** with encryption

### 4. Application Security
- **Change SECRET_KEY** from default
- **Enable rate limiting** for API endpoints
- **Input validation** on all forms
- **CSRF protection** (already enabled)

## Monitoring & Maintenance

### 1. Application Logs
```bash
# View application logs
tail -f admin.log

# View system logs
sudo journalctl -u car-admin -f
```

### 2. Health Checks
The admin UI includes built-in health monitoring:
- **Database connectivity** tests
- **AWS service** connection validation
- **Lambda function** status monitoring
- **API endpoint** availability checks

### 3. Backup Strategy
```bash
# Database backup
cp admin.db admin_backup_$(date +%Y%m%d).db

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp admin.db /backups/admin_${DATE}.db
find /backups -name "admin_*.db" -mtime +7 -delete
```

### 4. Updates
```bash
# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart car-admin
```

## Usage Guide

### Initial Setup
1. **Start the admin UI** using one of the deployment options above
2. **Navigate to Configuration** → Add your API credentials
3. **Test connections** using the Testing page
4. **Run a manual Lambda invocation** to verify everything works

### Daily Operations
- **Monitor the Dashboard** for system health and recent activity
- **Check Error Logs** for any issues that need attention
- **Review Transaction History** to verify automatic transfers
- **Use Testing Tools** to validate system components

### Troubleshooting
1. **Check Error Logs** first for detailed error information
2. **Use Testing Page** to isolate problems (API connectivity, Lambda function)
3. **Review Lambda CloudWatch logs** for detailed execution information
4. **Verify Configuration** settings for missing or incorrect values

## Features Summary

### ✅ CRUD Operations
- Complete configuration management with secure credential handling
- Transaction history with filtering and export capabilities
- Error log management with resolution tracking

### ✅ Error Logging
- Structured error logging with severity levels
- Detailed error information including stack traces
- Error investigation tools with pattern analysis
- Resolution tracking with notes

### ✅ Investigation Tools
- Real-time Lambda function monitoring
- CloudWatch log integration
- API connectivity testing
- System health monitoring
- Transaction analysis and reporting

The admin UI provides a comprehensive management interface that transforms your simple Lambda function into a fully monitored and manageable automated savings system.