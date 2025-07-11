# -*- coding: utf-8 -*-
import requests
import os
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIException(Exception):
    """Custom exception for API errors"""
    pass


class InvestecAPIClient:
    def __init__(self, client_id: str, secret_key: str, api_key: str):
        """
        Initialize the InvestecAPIClient with required credentials.
        
        Raises:
            ValueError: If any of client_id, secret_key, or api_key is missing.
        """
        if not all([client_id, secret_key, api_key]):
            raise ValueError("Client ID, Secret Key and API Key are all required")
        
        self.client_id = client_id
        self.secret_key = secret_key
        self.api_key = api_key
        self.session = requests.Session()
        self.token = None
        self.accounts = None
        self.token_expires_at = None

    def get_auth_token(self) -> None:
        """
        Obtains an OAuth2 authentication token from the Investec API, updating session headers and handling retries with exponential backoff on failure.
        
        Raises:
            APIException: If the token cannot be obtained after three attempts.
        """
        headers = {"x-api-key": self.api_key}
        
        for attempt in range(3):
            try:
                logger.info(f"Attempting to get auth token (attempt {attempt + 1})")
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
                self.token = token_data["access_token"]
                
                # Set token expiration (default to 1 hour if not provided)
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                })
                
                logger.info("Successfully obtained auth token")
                return
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Auth token attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    raise APIException(f"Failed to get auth token after 3 attempts: {e}") from e
                time.sleep(2 ** attempt)  # Exponential backoff

    def is_token_expired(self) -> bool:
        """
        Determine whether the current authentication token is expired or will expire within the next five minutes.
        
        Returns:
            bool: True if the token is missing or expiring soon; otherwise, False.
        """
        if not self.token_expires_at:
            return True
        return time.time() >= self.token_expires_at - 300  # Refresh 5 minutes before expiry

    def ensure_valid_token(self) -> None:
        """
        Ensures that a valid authentication token is available, refreshing it if missing or expired.
        """
        if not self.token or self.is_token_expired():
            self.get_auth_token()

    def get_accounts(self) -> None:
        """
        Retrieves and stores the list of accounts from the Investec API.
        
        Raises:
            APIException: If the API request fails or returns an error.
        """
        self.ensure_valid_token()
        
        try:
            logger.info("Fetching accounts from Investec API")
            response = self.session.get(
                "https://openapi.investec.com/za/pb/v1/accounts",
                timeout=30
            )
            response.raise_for_status()
            
            self.accounts = response.json()["data"]["accounts"]
            logger.info(f"Successfully fetched {len(self.accounts)} accounts")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch accounts: {e}")
            raise APIException(f"Failed to fetch accounts: {e}")

    def transfer(self, from_account: str, to_account: str, amount: float, 
                from_reference: str, to_reference: str) -> Dict[str, Any]:
        """
                Transfers a specified amount of money from one Investec account to another.
                
                Parameters:
                    from_account (str): The source account ID.
                    to_account (str): The destination account ID.
                    amount (float): The amount to transfer; must be positive.
                    from_reference (str): Reference for the sender.
                    to_reference (str): Reference for the recipient.
                
                Returns:
                    Dict[str, Any]: The API response containing transfer details.
                
                Raises:
                    ValueError: If the transfer amount is not positive.
                    APIException: If the transfer request fails.
                """
        self.ensure_valid_token()
        
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
            
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
        
        try:
            logger.info(f"Initiating transfer of R{amount:.2f} from {from_account} to {to_account}")
            response = self.session.post(
                "https://openapi.investec.com/za/pb/v1/accounts/transfermultiple",
                json=transfer_data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Transfer successful: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Transfer failed: {e}")
            raise APIException(f"Transfer failed: {e}")


class CarTrackAPIClient:
    def __init__(self, username: str, api_key: str):
        """
        Initialize the CarTrackAPIClient with the provided username and API key.
        
        Raises:
            ValueError: If either the username or API key is missing.
        """
        if not all([username, api_key]):
            raise ValueError("Username and API Key are both required")
        
        self.username = username
        self.api_key = api_key
        self.session = requests.Session()
        self.trips = None
        self.distance = 0

    def get_trips(self, registration: str, from_date: str, to_date: str) -> None:
        """
        Fetches trip data for a specific vehicle registration from the CarTrack API within a given date range, retrying up to three times on failure.
        
        Raises:
            ValueError: If any of the required parameters (registration, from_date, to_date) are missing.
            APIException: If the API request fails after three attempts.
        """
        if not all([registration, from_date, to_date]):
            raise ValueError("Registration, from_date and to_date are all required")
            
        for attempt in range(3):
            try:
                logger.info(f"Fetching trips for {registration} from {from_date} to {to_date} (attempt {attempt + 1})")
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
                logger.info(f"Successfully fetched {len(self.trips)} trips")
                return
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Get trips attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    raise APIException(f"Failed to get trips after 3 attempts: {e}") from e
                time.sleep(2 ** attempt)  # Exponential backoff

    def calculate_distance(self, registration: str, from_date: str, to_date: str) -> float:
        """
        Calculates the total distance traveled by a vehicle within a specified date range.
        
        Retrieves trip data for the given vehicle registration and date range, sums the trip distances (in meters), converts the total to kilometers, and returns the result. If no trips are found, returns 0.
         
        Parameters:
            registration (str): The vehicle registration identifier.
            from_date (str): The start date in "YYYY-MM-DD" format.
            to_date (str): The end date in "YYYY-MM-DD" format.
        
        Returns:
            float: The total distance traveled in kilometers.
        """
        self.get_trips(registration, from_date, to_date)
        
        if not self.trips:
            logger.warning("No trips found for the specified period")
            self.distance = 0
            return 0
            
        total_distance = 0
        for trip in self.trips:
            trip_distance = int(trip.get("trip_distance", 0))
            total_distance += trip_distance
            
        # Convert from meters to kilometers
        self.distance = total_distance / 1000.0
        logger.info(f"Total distance calculated: {self.distance:.2f} km")
        return self.distance


def get_date_range() -> tuple:
    """
    Return a tuple containing yesterday's date as both the start and end date in "YYYY-MM-DD" format.
    
    Returns:
        tuple: (from_date, to_date) where both are yesterday's date strings.
    """
    yesterday = datetime.now() - timedelta(days=1)
    from_date = yesterday.strftime("%Y-%m-%d")
    to_date = yesterday.strftime("%Y-%m-%d")
    return from_date, to_date


def validate_environment() -> Dict[str, str]:
    """
    Validates the presence and correctness of required environment variables for API operations.
    
    Checks that all necessary environment variables are set and that `rate_per_km` is a valid number. Raises a ValueError if any variables are missing or if `rate_per_km` is not numeric.
    
    Returns:
        dict: A dictionary containing the validated environment variables and their values.
    """
    required_vars = [
        "investec_client_id",
        "investec_secret_key", 
        "investec_api_key",
        "investec_from_account_id",
        "investec_to_account_id",
        "cartrack_username",
        "cartrack_password",
        "car_registration",
        "rate_per_km"
    ]
    
    env_vars = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            env_vars[var] = value
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Validate numeric values
    try:
        float(env_vars["rate_per_km"])
    except ValueError:
        raise ValueError("rate_per_km must be a valid number")
    
    return env_vars


def handler(event, context):
    """
    AWS Lambda entry point for automating money transfers based on vehicle trip distances.
    
    This function validates environment variables, determines the date range and car registration (with optional overrides from the event), calculates the total distance traveled using the CarTrack API, and, if distance is nonzero, calculates the transfer amount and performs a transfer between Investec accounts. Returns a JSON response with transfer details on success, or an error message on failure.
    
    Parameters:
        event (dict): Lambda event payload, optionally containing 'from_date', 'to_date', and 'car_registration'.
        context: Lambda context object (unused).
    
    Returns:
        dict: JSON-serializable response with HTTP status code and result or error details.
    """
    try:
        logger.info("Starting CarTrack to Investec transfer process")
        
        # Validate environment variables
        env_vars = validate_environment()
        
        # Get date range (default to yesterday, but allow override from event)
        if event and "from_date" in event and "to_date" in event:
            from_date = event["from_date"]
            to_date = event["to_date"]
            logger.info(f"Using dates from event: {from_date} to {to_date}")
        else:
            from_date, to_date = get_date_range()
            logger.info(f"Using automatic date range: {from_date} to {to_date}")
        
        # Get car registration (allow override from event)
        car_registration = event.get("car_registration", env_vars["car_registration"]) if event else env_vars["car_registration"]
        
        # Initialize CarTrack client
        cartrack = CarTrackAPIClient(
            env_vars["cartrack_username"],
            env_vars["cartrack_password"]
        )
        
        # Calculate distance
        distance = cartrack.calculate_distance(car_registration, from_date, to_date)
        
        if distance == 0:
            logger.info("No distance traveled, skipping transfer")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No distance traveled, no transfer made',
                    'distance': distance,
                    'from_date': from_date,
                    'to_date': to_date
                })
            }
        
        # Calculate transfer amount
        rate_per_km = float(env_vars["rate_per_km"])
        transfer_amount = distance * rate_per_km
        
        # Initialize Investec client
        investec = InvestecAPIClient(
            env_vars["investec_client_id"],
            env_vars["investec_secret_key"],
            env_vars["investec_api_key"]
        )
        
        # Perform transfer
        transfer_result = investec.transfer(
            env_vars["investec_from_account_id"],
            env_vars["investec_to_account_id"],
            transfer_amount,
            f"CarTrack {from_date}",
            f"CarTrack {from_date}"
        )
        
        success_message = f"Successfully transferred R{transfer_amount:.2f} for {distance:.2f}km traveled"
        logger.info(success_message)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': success_message,
                'distance': distance,
                'transfer_amount': transfer_amount,
                'rate_per_km': rate_per_km,
                'from_date': from_date,
                'to_date': to_date,
                'transfer_result': transfer_result
            })
        }
        
    except Exception as e:
        error_message = f"Error processing CarTrack to Investec transfer: {str(e)}"
        logger.error(error_message, exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message,
                'message': 'Transfer failed'
            })
        }
