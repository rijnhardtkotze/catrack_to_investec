# Car Service Savings Management Admin UI

A comprehensive web-based management interface for monitoring and managing your car service savings Lambda function.

## Features

### 🔧 Configuration Management (CRUD)
- **Create/Read/Update/Delete** configuration settings
- **Secure credential management** with masked sensitive data
- **Environment variable synchronization** with Lambda function
- **Configuration history tracking**

### 📊 Error Logging & Monitoring
- **Structured error logging** with severity levels (INFO, WARNING, ERROR, CRITICAL)
- **Detailed error information** including stack traces and context
- **Error resolution tracking** with resolution notes
- **Search and filter** errors by type, severity, and status
- **Error investigation tools** with related error linking

### 🔍 Investigations & Analytics
- **Transaction history** with detailed filtering and search
- **Lambda function monitoring** with CloudWatch integration
- **API connection testing** for CarTrack and Investec APIs
- **Real-time logs** from CloudWatch
- **Performance metrics** and system health monitoring

### 🧪 Testing Tools
- **Manual Lambda invocation** with custom parameters
- **Distance calculation testing** with different date ranges
- **API connectivity testing** for all external services
- **Pre-defined test scenarios** for common use cases
- **Test result history** with detailed logging

## Architecture

### Frontend
- **Flask web application** with Bootstrap 5 UI
- **Responsive design** that works on desktop and mobile
- **Real-time updates** with automatic refresh capabilities
- **Interactive forms** with validation and error handling

### Backend
- **SQLAlchemy ORM** with SQLite database (easily upgradable to PostgreSQL)
- **AWS SDK integration** for Lambda, CloudWatch, and DynamoDB
- **Structured logging** with multiple output destinations
- **RESTful API endpoints** for AJAX interactions

### Database Schema
```sql
-- Configuration settings
CREATE TABLE configuration (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Transaction logs
CREATE TABLE transaction_log (
    id INTEGER PRIMARY KEY,
    transaction_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    amount FLOAT,
    distance FLOAT,
    from_account VARCHAR(100),
    to_account VARCHAR(100),
    reference VARCHAR(200),
    error_message TEXT,
    raw_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Error logs
CREATE TABLE error_log (
    id INTEGER PRIMARY KEY,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    function_name VARCHAR(100),
    lambda_request_id VARCHAR(100),
    user_agent VARCHAR(200),
    ip_address VARCHAR(50),
    additional_data TEXT,
    severity VARCHAR(20) DEFAULT 'ERROR',
    resolved BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Installation

### Quick Setup
```bash
cd admin_ui
./setup.sh
```

### Manual Setup
1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**:
   ```bash
   python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

5. **Run the application**:
   ```bash
   python3 run.py
   ```

## Configuration

### Environment Variables
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=development
DATABASE_URL=sqlite:///admin.db

# AWS Configuration
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Lambda Function Configuration
LAMBDA_FUNCTION_NAME=cartrack_to_investec
LAMBDA_LOG_GROUP=/aws/lambda/cartrack_to_investec

# DynamoDB Tables (optional)
TRANSACTION_TABLE=car-service-transactions
ERROR_TABLE=car-service-errors

# Admin UI Configuration
PORT=5000
```

### AWS IAM Permissions
The admin UI requires the following AWS permissions:
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

## Usage

### Dashboard
- **Overview metrics** showing transaction counts, monthly savings, and error status
- **Recent transactions** with quick access to details
- **Unresolved errors** with one-click resolution
- **Lambda function status** with real-time logs

### Configuration Management
1. Navigate to **Configuration** → **Settings**
2. Click **Add Configuration** to create new settings
3. Edit existing configurations by clicking the edit icon
4. **Sensitive data** (passwords, keys) are automatically masked for security

### Error Investigation
1. Go to **Error Logs** to view all errors
2. Filter by **severity**, **resolution status**, or **date range**
3. Click on an error to view **detailed information**
4. Use **investigation tools** to analyze patterns and root causes
5. **Mark errors as resolved** with resolution notes

### Testing & Debugging
1. Visit the **Testing** page for manual operations
2. **Test API connections** to verify external service availability
3. **Manually invoke Lambda** with custom parameters
4. **Run test scenarios** to validate different use cases
5. **View test history** to track testing activities

## API Endpoints

### Configuration API
- `GET /config` - List all configurations
- `POST /config/new` - Create new configuration
- `PUT /config/<id>/edit` - Update configuration
- `DELETE /config/<id>/delete` - Delete configuration

### Transaction API
- `GET /transactions` - List transactions with filtering
- `GET /transactions/<id>` - Get transaction details

### Error API
- `GET /errors` - List errors with filtering
- `GET /errors/<id>` - Get error details
- `POST /errors/<id>/resolve` - Mark error as resolved

### Lambda API
- `POST /api/lambda/invoke` - Manually invoke Lambda function
- `GET /api/lambda/logs` - Get recent Lambda logs

## Security Features

### Data Protection
- **Sensitive data masking** in the UI
- **Secure credential storage** recommendations
- **Input validation** and sanitization
- **CSRF protection** on all forms

### Access Control
- **Environment-based configuration** separation
- **AWS IAM integration** for service access
- **Audit logging** for all administrative actions

### Production Deployment
- **Environment variable validation**
- **Secure secret management** with AWS Secrets Manager
- **HTTPS enforcement** recommendations
- **Database encryption** support

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Reset database
rm admin.db
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

**AWS Permission Errors**
- Verify IAM role has required permissions
- Check AWS credentials configuration
- Validate region settings

**Lambda Invocation Failures**
- Ensure Lambda function exists and is deployable
- Verify function configuration matches admin UI settings
- Check CloudWatch logs for detailed error messages

### Debug Mode
Enable debug logging by setting:
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
```

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly using the built-in testing tools
5. Submit a pull request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names
- Include docstrings for functions and classes
- Add comments for complex logic

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
1. Check the **Error Logs** in the admin UI
2. Review **Lambda function logs** in CloudWatch
3. Use the **Testing Tools** to isolate problems
4. Check the **Configuration** settings for missing values