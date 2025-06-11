#!/bin/bash

# Car Service Savings Admin UI Setup Script

echo "🚗 Setting up Car Service Savings Admin UI..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python packages..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating .env configuration file..."
    cat > .env << EOL
# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=development
DATABASE_URL=sqlite:///admin.db

# AWS Configuration
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Lambda Function Configuration
LAMBDA_FUNCTION_NAME=cartrack_to_investec
LAMBDA_LOG_GROUP=/aws/lambda/cartrack_to_investec

# DynamoDB Tables (optional)
TRANSACTION_TABLE=car-service-transactions
ERROR_TABLE=car-service-errors

# Admin UI Configuration
PORT=5000
EOL
    echo "📝 Created .env file. Please edit it with your AWS credentials and configuration."
fi

# Initialize database
echo "🗄️ Initializing database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized successfully!')"

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit the .env file with your AWS configuration"
echo "2. Run the application: python3 run.py"
echo "3. Open http://localhost:5000 in your browser"
echo ""
echo "🔐 Security reminder:"
echo "- Change the SECRET_KEY in .env before production deployment"
echo "- Set up proper AWS IAM roles and policies"
echo "- Use AWS Secrets Manager for sensitive configuration in production"