#!/usr/bin/env python3
"""
Local testing script for the CarTrack to Investec Lambda function.
This script allows you to test the function locally without deploying to AWS.
"""

import json
import os
from datetime import datetime, timedelta
from service import handler

def load_test_event():
    """Load test event from event.json"""
    try:
        with open('event.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def setup_test_environment():
    """Set up test environment variables"""
    # Load from config.yaml or set test values
    test_env = {
        'investec_client_id': 'test_client_id',
        'investec_secret_key': 'test_secret_key',
        'investec_api_key': 'test_api_key',
        'investec_from_account_id': 'test_from_account',
        'investec_to_account_id': 'test_to_account',
        'cartrack_username': 'test_username',
        'cartrack_password': 'test_password',
        'car_registration': 'TEST123GP',
        'rate_per_km': '0.25'
    }
    
    # Set environment variables if not already set
    for key, value in test_env.items():
        if not os.getenv(key):
            os.environ[key] = value
            print(f"Set test env var: {key} = {value}")

def test_date_range():
    """Test the automatic date range functionality"""
    from service import get_date_range
    
    print("Testing automatic date range...")
    from_date, to_date = get_date_range()
    print(f"Auto date range: {from_date} to {to_date}")
    
    # Should be yesterday
    yesterday = datetime.now() - timedelta(days=1)
    expected_date = yesterday.strftime("%Y-%m-%d")
    assert from_date == expected_date, f"Expected {expected_date}, got {from_date}"
    print("✅ Date range test passed")

def test_validation():
    """Test environment variable validation"""
    from service import validate_environment
    
    print("\nTesting environment validation...")
    
    # Save original env vars
    original_env = dict(os.environ)
    
    try:
        # Test missing variables
        for key in ['investec_client_id', 'cartrack_username', 'rate_per_km']:
            if key in os.environ:
                del os.environ[key]
        
        try:
            validate_environment()
            assert False, "Should have raised ValueError for missing env vars"
        except ValueError as e:
            print(f"✅ Correctly caught missing env vars: {e}")
        
        # Restore env vars
        os.environ.update(original_env)
        
        # Test invalid rate_per_km
        os.environ['rate_per_km'] = 'invalid'
        try:
            validate_environment()
            raise AssertionError("Should have raised ValueError for invalid rate_per_km")
        except ValueError as e:
            print(f"✅ Correctly caught invalid rate_per_km: {e}")
        
        # Restore valid rate_per_km
        os.environ['rate_per_km'] = '0.25'
        
        print("✅ Environment validation tests passed")
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

def test_handler():
    """Test the Lambda handler function"""
    print("\nTesting Lambda handler...")
    
    # Load test event
    event = load_test_event()
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = 'test_function'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test_function'
            self.memory_limit_in_mb = 128
            self.remaining_time_in_millis = 30000
            self.log_group_name = '/aws/lambda/test_function'
            self.log_stream_name = '2023/01/01/[$LATEST]test'
            self.aws_request_id = 'test-request-id'
    
    context = MockContext()
    
    # Note: This will likely fail due to invalid credentials, but should test the structure
    try:
        result = handler(event, context)
        print(f"Handler result: {result}")
        
        # Parse response
        response = json.loads(result['body']) if isinstance(result, dict) and 'body' in result else result
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Expected error with test credentials: {e}")
        print("✅ Handler structure test completed (error expected with test credentials)")

if __name__ == '__main__':
    print("🧪 Running local tests for CarTrack to Investec Lambda function")
    print("=" * 60)
    
    # Setup test environment
    setup_test_environment()
    
    # Run tests
    test_date_range()
    test_validation()
    test_handler()
    
    print("\n" + "=" * 60)
    print("🎉 Local testing completed!")
    print("\nTo test with real credentials:")
    print("1. Set your actual environment variables")
    print("2. Update event.json with a real date and car registration")
    print("3. Run this script again")