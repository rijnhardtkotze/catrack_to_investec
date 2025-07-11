# CarTrack to Investec Auto-Transfer

This AWS Lambda function automatically transfers money to your Investec savings account based on your actual driving distance from CarTrack. Perfect for building a car service fund based on real usage!

## Features

- ✅ Automatic date selection (processes yesterday's trips by default)
- ✅ Robust error handling with retry logic
- ✅ Comprehensive logging for debugging
- ✅ Configurable via environment variables
- ✅ Support for manual date/registration override via Lambda event
- ✅ Proper API token management with automatic refresh

## Setup Instructions

### 1. Prerequisites
- AWS account with Lambda access
- Investec Private Banking API access
- CarTrack fleet API access
- Python 3.9+

### 2. Installation
The local dev environment and deploy mechanism is handled through this toolset: https://github.com/nficano/python-lambda

```bash
pip install python-lambda
```

### 3. Configuration
1. Fill in the `config.yaml` file with your details:
   - Add your Investec API credentials
   - Add your CarTrack username and password
   - Set your car registration number
   - Configure the rate per kilometer

2. Test locally:
```bash
lambda invoke -v
```

3. Deploy:
```bash
lambda deploy
```

### 4. Manual Usage
You can override the default behavior by passing an event:
```json
{
  "from_date": "2022-04-01",
  "to_date": "2022-04-01",
  "car_registration": "ABC123GP"
}
```

## Environment Variables

All sensitive data should be stored as environment variables:

| Variable | Description |
|----------|-------------|
| `investec_client_id` | Your Investec API client ID |
| `investec_secret_key` | Your Investec API secret key |
| `investec_api_key` | Your Investec API key |
| `investec_from_account_id` | Source account ID |
| `investec_to_account_id` | Destination account ID |
| `cartrack_username` | CarTrack username |
| `cartrack_password` | CarTrack password |
| `car_registration` | Your car registration number |
| `rate_per_km` | Rate per kilometer (e.g., "0.25") |

## Scheduling

Set up a CloudWatch Events rule to trigger this Lambda daily:
```bash
aws events put-rule --name cartrack-daily --schedule-expression "cron(0 8 * * ? *)"
```

## Monitoring

The function returns proper HTTP status codes and detailed JSON responses for monitoring:
- 200: Success
- 500: Error (check CloudWatch logs)

## Security

- Never commit credentials to version control
- Use IAM roles with minimal required permissions
- Enable CloudTrail for API call auditing
