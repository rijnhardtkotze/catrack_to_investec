# -*- coding: utf-8 -*-
import requests
import os
import json
import logging
import traceback
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize DynamoDB for logging (optional)
try:
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
    transaction_table = dynamodb.Table(os.environ.get('TRANSACTION_TABLE', 'car-service-transactions'))
    error_table = dynamodb.Table(os.environ.get('ERROR_TABLE', 'car-service-errors'))
except Exception as e:
    logger.warning(f"Could not initialize DynamoDB: {e}")
    dynamodb = transaction_table = error_table = None


def log_transaction(transaction_type, status, amount=None, distance=None, from_account=None, 
                   to_account=None, reference=None, error_message=None, raw_data=None):
    """Log transaction to both CloudWatch and DynamoDB"""
    transaction_data = {
        'transaction_type': transaction_type,
        'status': status,
        'amount': amount,
        'distance': distance,
        'from_account': from_account,
        'to_account': to_account,
        'reference': reference,
        'error_message': error_message,
        'raw_data': raw_data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Log to CloudWatch
    logger.info(f"Transaction {transaction_type}: {status}", extra=transaction_data)
    
    # Log to DynamoDB if available
    if transaction_table:
        try:
            transaction_table.put_item(Item={
                'id': f"{transaction_type}_{datetime.utcnow().isoformat()}",
                **transaction_data
            })
        except Exception as e:
            logger.error(f"Failed to log transaction to DynamoDB: {e}")


def log_error(error_type, error_message, function_name=None, request_id=None, 
              stack_trace=None, additional_data=None, severity='ERROR'):
    """Log error to both CloudWatch and DynamoDB"""
    error_data = {
        'error_type': error_type,
        'error_message': str(error_message),
        'function_name': function_name,
        'lambda_request_id': request_id,
        'stack_trace': stack_trace,
        'additional_data': additional_data,
        'severity': severity,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Log to CloudWatch
    logger.error(f"Error {error_type}: {error_message}", extra=error_data)
    
    # Log to DynamoDB if available
    if error_table:
        try:
            error_table.put_item(Item={
                'id': f"{error_type}_{datetime.utcnow().isoformat()}",
                **error_data
            })
        except Exception as e:
            logger.error(f"Failed to log error to DynamoDB: {e}")


class InvestecAPIClient(object):
    def __init__(self, client_id: str, secret_key: str, api_key: str):
        if not client_id or not secret_key or not api_key:
            raise ValueError("Client, Secret and API Key Needed")
        self.client_id = client_id
        self.secret_key = secret_key
        self.api_key = api_key
        self.session = requests.Session()
        self.token = None
        self.accounts = None

    def get_auth_token(self) -> None:
        try:
            headers = {"x-api-key": self.api_key}
            response = requests.post(
                'https://openapi.investec.com/identity/v2/oauth2/token',
                data={
                    'grant_type': 'client_credentials',
                    'scope': 'accounts'
                },
                headers=headers,
                auth=(self.client_id, self.secret_key),
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.session.headers = {
                'Authorization': 'Bearer ' + token_data["access_token"]
            }
            self.token = token_data["access_token"]
            
            logger.info("Successfully obtained Investec API token")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get Investec auth token: {e}"
            log_error('InvestecAuthError', error_msg, 'get_auth_token', 
                     stack_trace=traceback.format_exc())
            raise
        except KeyError as e:
            error_msg = f"Invalid token response format: {e}"
            log_error('InvestecTokenError', error_msg, 'get_auth_token',
                     stack_trace=traceback.format_exc())
            raise

    def get_accounts(self) -> None:
        try:
            r = self.session.get("https://openapi.investec.com/za/pb/v1/accounts", timeout=30)
            r.raise_for_status()
            account_data = r.json()
            self.accounts = account_data["data"]["accounts"]
            
            logger.info(f"Retrieved {len(self.accounts)} Investec accounts")
            log_transaction('account_fetch', 'success', raw_data=json.dumps(account_data))
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get Investec accounts: {e}"
            log_error('InvestecAccountError', error_msg, 'get_accounts',
                     stack_trace=traceback.format_exc())
            log_transaction('account_fetch', 'failed', error_message=error_msg)
            raise
        except KeyError as e:
            error_msg = f"Invalid accounts response format: {e}"
            log_error('InvestecAccountError', error_msg, 'get_accounts',
                     stack_trace=traceback.format_exc())
            raise

    def transfer(self, from_account, to_account, amount, from_reference, to_reference) -> None:
        try:
            transfer_data = {
                "AccountId": from_account,
                "TransferList": [
                    {
                        "BeneficiaryAccountId": to_account,
                        "Amount": amount,
                        "MyReference": from_reference,
                        "TheirReference": to_reference
                    }
                ]
            }
            
            r = self.session.post(
                "https://openapi.investec.com/za/pb/v1/accounts/transfermultiple",
                json=transfer_data,
                timeout=30
            )
            r.raise_for_status()
            
            response_data = r.json() if r.content else {}
            
            logger.info(f"Successfully transferred R{amount:.2f} from {from_account} to {to_account}")
            log_transaction('transfer', 'success', amount=amount, 
                          from_account=from_account, to_account=to_account,
                          reference=from_reference, raw_data=json.dumps(response_data))
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to transfer R{amount:.2f}: {e}"
            log_error('InvestecTransferError', error_msg, 'transfer',
                     stack_trace=traceback.format_exc(),
                     additional_data=json.dumps({
                         'from_account': from_account,
                         'to_account': to_account,
                         'amount': amount
                     }))
            log_transaction('transfer', 'failed', amount=amount,
                          from_account=from_account, to_account=to_account,
                          reference=from_reference, error_message=error_msg)
            raise


class CarTrackAPIClient(object):
    def __init__(self, username: str, api_key: str):
        if not username or not api_key or not api_key:
            raise ValueError("Username and API Key is needed")
        self.username = username
        self.api_key = api_key
        self.session = requests.Session()
        self.trips = None
        self.distance = 0

    def get_trips(self, registration, from_date, to_date):
        try:
            response = self.session.get(
                "https://fleetapi-za.cartrack.com/rest/get_all_trips",
                params={
                    "reg": registration,
                    "start_ts": from_date,
                    "end_ts": to_date
                },
                auth=(self.username, self.api_key),
                timeout=30
            )
            response.raise_for_status()
            self.trips = response.json()
            
            logger.info(f"Retrieved {len(self.trips)} trips for {registration}")
            log_transaction('trip_fetch', 'success', 
                          raw_data=json.dumps({
                              'registration': registration,
                              'from_date': from_date,
                              'to_date': to_date,
                              'trip_count': len(self.trips)
                          }))
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get trips for {registration}: {e}"
            log_error('CarTrackTripError', error_msg, 'get_trips',
                     stack_trace=traceback.format_exc(),
                     additional_data=json.dumps({
                         'registration': registration,
                         'from_date': from_date,
                         'to_date': to_date
                     }))
            log_transaction('trip_fetch', 'failed', error_message=error_msg)
            raise

    def calculate_distance(self, registration, from_date, to_date):
        try:
            self.get_trips(registration, from_date, to_date)
            distance = 0
            
            for trip in self.trips:
                try:
                    trip_distance = int(trip.get("trip_distance", 0))
                    distance += trip_distance
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid trip distance data: {trip.get('trip_distance')} - {e}")
                    continue
            
            self.distance = distance / 1000.0  # Convert to kilometers
            
            logger.info(f"Calculated total distance: {self.distance:.2f}km for {registration}")
            log_transaction('distance_calculation', 'success', 
                          distance=self.distance,
                          raw_data=json.dumps({
                              'registration': registration,
                              'from_date': from_date,
                              'to_date': to_date,
                              'total_distance_meters': distance,
                              'total_distance_km': self.distance
                          }))
            
        except Exception as e:
            error_msg = f"Failed to calculate distance for {registration}: {e}"
            log_error('CarTrackDistanceError', error_msg, 'calculate_distance',
                     stack_trace=traceback.format_exc(),
                     additional_data=json.dumps({
                         'registration': registration,
                         'from_date': from_date,
                         'to_date': to_date
                     }))
            log_transaction('distance_calculation', 'failed', error_message=error_msg)
            raise


def handler(event, context):
    """
    AWS Lambda handler function for automated car service savings
    """
    request_id = context.aws_request_id if context else 'local'
    
    try:
        logger.info(f"Lambda function started - Request ID: {request_id}")
        
        # Get configuration from environment variables
        config = {
            'investec_client_id': os.getenv("investec_client_id"),
            'investec_secret_key': os.getenv("investec_secret_key"),
            'investec_api_key': os.getenv("investec_api_key"),
            'cartrack_username': os.getenv("cartrack_username"),
            'cartrack_password': os.getenv("cartrack_password"),
            'from_account_id': os.getenv("investec_from_account_id"),
            'to_account_id': os.getenv("investec_to_account_id"),
            'rate_per_km': float(os.getenv("rate_per_km", "0.25")),
            'registration': os.getenv("vehicle_registration", "DV77FCGP")
        }
        
        # Validate required configuration
        missing_config = [key for key, value in config.items() if not value]
        if missing_config:
            error_msg = f"Missing required configuration: {', '.join(missing_config)}"
            log_error('ConfigurationError', error_msg, 'handler', request_id, severity='CRITICAL')
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_msg})
            }
        
        # Get date range from event or use defaults
        from_date = event.get('from_date', '2022-03-31') if event else '2022-03-31'
        to_date = event.get('to_date', '2022-04-01') if event else '2022-04-01'
        
        # Initialize API clients
        investec = InvestecAPIClient(
            config['investec_client_id'],
            config['investec_secret_key'],
            config['investec_api_key']
        )
        
        cartrack = CarTrackAPIClient(
            config['cartrack_username'],
            config['cartrack_password']
        )
        
        # Get authentication token
        investec.get_auth_token()
        
        # Calculate distance
        cartrack.calculate_distance(config['registration'], from_date, to_date)
        
        # Calculate transfer amount
        transfer_amount = cartrack.distance * config['rate_per_km']
        
        if transfer_amount <= 0:
            logger.warning("Transfer amount is zero or negative, skipping transfer")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No transfer needed',
                    'distance': cartrack.distance,
                    'amount': transfer_amount
                })
            }
        
        # Perform transfer
        investec.transfer(
            config['from_account_id'],
            config['to_account_id'],
            transfer_amount,
            f"CarTrack Auto-Save ({from_date} to {to_date})",
            f"Distance: {cartrack.distance:.2f}km @ R{config['rate_per_km']}/km"
        )
        
        # Log successful completion
        result = {
            'distance': cartrack.distance,
            'rate_per_km': config['rate_per_km'],
            'transfer_amount': transfer_amount,
            'from_date': from_date,
            'to_date': to_date,
            'registration': config['registration']
        }
        
        logger.info(f"Lambda function completed successfully - Transfer: R{transfer_amount:.2f}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Transfer completed successfully',
                **result
            })
        }
        
    except Exception as e:
        error_msg = f"Lambda function failed: {e}"
        log_error('LambdaHandlerError', error_msg, 'handler', request_id,
                 stack_trace=traceback.format_exc(), severity='CRITICAL')
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'request_id': request_id
            })
        }
