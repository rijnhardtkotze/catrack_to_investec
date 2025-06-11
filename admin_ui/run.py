#!/usr/bin/env python3
"""
Production runner for the Car Service Savings Admin UI
"""

import os
from dotenv import load_dotenv
from app import app, db

# Load environment variables
load_dotenv()

if __name__ == '__main__':
    # Ensure database is created
    with app.app_context():
        db.create_all()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)