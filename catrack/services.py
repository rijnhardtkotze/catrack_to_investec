"""
Services module that wraps the original service.py functionality
"""
import logging
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

# Import service module - now properly structured
import service

from .models import APIConfiguration, Trip, Transfer, CarRegistration, InvestecAccount

logger = logging.getLogger(__name__)


class CarTrackService:
    """Service class to handle CarTrack API interactions"""
    
    def __init__(self):
        config = APIConfiguration.objects.filter(api_type='cartrack', is_active=True).first()
        if not config:
            raise ValueError("No active CarTrack API configuration found")
        
        # Use the stored password if available, otherwise fall back to plain password
        password = config.password
        if password and password.startswith('pbkdf2_'):
            # For hashed passwords, we'd need to store plain passwords separately
            # or implement a different approach for API authentication
            logger.warning("Using hashed password for API - consider secure credential storage")
        
        self.client = service.CarTrackAPIClient(
            username=config.username,
            api_key=config.api_key
        )
    
    def fetch_and_store_trips(self, registration_number, from_date, to_date):
        """Fetch trips from CarTrack API and store in database"""
        try:
            car_reg = CarRegistration.objects.get(registration_number=registration_number)
        except CarRegistration.DoesNotExist:
            raise ValueError(f"Car registration '{registration_number}' not found")
        
        self.client.get_trips(registration_number, from_date, to_date)
        
        if self.client.trips:
            for trip_data in self.client.trips:
                # Convert timestamps with validation
                try:
                    start_ts_raw = trip_data.get('start_ts')
                    end_ts_raw = trip_data.get('end_ts')
                    
                    if start_ts_raw is None or end_ts_raw is None:
                        logger.warning(f"Missing timestamp data in trip: {trip_data}")
                        continue
                    
                    # Validate that timestamps are numeric
                    start_ts_int = int(start_ts_raw)
                    end_ts_int = int(end_ts_raw)
                    
                    # Convert to timezone-aware datetime objects
                    start_ts = timezone.make_aware(datetime.fromtimestamp(start_ts_int))
                    end_ts = timezone.make_aware(datetime.fromtimestamp(end_ts_int))
                    
                except (ValueError, TypeError, OverflowError) as e:
                    logger.error(f"Invalid timestamp format in trip data: {e}")
                    continue
                
                Trip.objects.get_or_create(
                    car_registration=car_reg,
                    trip_distance=int(trip_data.get('trip_distance', 0)),
                    start_timestamp=start_ts,
                    end_timestamp=end_ts,
                    defaults={
                        'raw_data': trip_data
                    }
                )
        
        return self.client.trips
    
    def calculate_total_distance(self, registration_number, from_date, to_date):
        """Calculate total distance for a period"""
        self.client.calculate_distance(registration_number, from_date, to_date)
        return self.client.distance


class InvestecService:
    """Service class to handle Investec API interactions"""
    
    def __init__(self):
        config = APIConfiguration.objects.filter(api_type='investec', is_active=True).first()
        if not config:
            raise ValueError("No active Investec API configuration found")
        
        self.client = service.InvestecAPIClient(
            client_id=config.client_id,
            secret_key=config.secret_key,
            api_key=config.api_key
        )
        
        # Get authentication token
        self.client.get_auth_token()
    
    def create_transfer(self, car_registration, distance_km, from_date, to_date):
        """Create a transfer based on distance calculation"""
        with transaction.atomic():
            try:
                car_reg = CarRegistration.objects.get(registration_number=car_registration)
            except CarRegistration.DoesNotExist:
                raise ValueError(f"Car registration '{car_registration}' not found")
            
            # Calculate amount
            amount = Decimal(str(distance_km)) * car_reg.rate_per_km
            
            # Get default accounts
            from_account = InvestecAccount.objects.filter(account_type='from', is_active=True).first()
            to_account = InvestecAccount.objects.filter(account_type='to', is_active=True).first()
            
            if not from_account or not to_account:
                raise ValueError("No active from/to accounts configured")
            
            # Validate and parse to_date
            try:
                transfer_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            except ValueError as e:
                raise ValueError(f"Invalid date format for to_date '{to_date}'. Expected YYYY-MM-DD: {e}")
            
            # Create transfer record
            transfer = Transfer.objects.create(
                car_registration=car_reg,
                from_account=from_account,
                to_account=to_account,
                amount=amount,
                distance_km=Decimal(str(distance_km)),
                rate_per_km=car_reg.rate_per_km,
                from_reference="CarTrack Auto",
                to_reference="CarTrack Auto",
                transfer_date=transfer_date
            )
            
            try:
                # Execute the transfer via API
                self.client.transfer(
                    from_account=from_account.account_id,
                    to_account=to_account.account_id,
                    amount=float(amount),
                    from_reference=transfer.from_reference,
                    to_reference=transfer.to_reference
                )
                
                transfer.status = 'completed'
                transfer.save()
                
            except Exception as e:
                transfer.status = 'failed'
                transfer.save()
                logger.error(f"Transfer API call failed: {e}")
                raise e
            
            return transfer


class CarTrackToInvestecService:
    """Main service that orchestrates the CarTrack to Investec process"""
    
    def process_distance_transfer(self, registration_number, from_date, to_date):
        """Main process to calculate distance and create transfer"""
        
        # Validate input parameters
        if not all([registration_number, from_date, to_date]):
            raise ValueError("registration_number, from_date, and to_date are required")
        
        # Initialize services
        cartrack = CarTrackService()
        investec = InvestecService()
        
        # Fetch and store trips
        trips = cartrack.fetch_and_store_trips(registration_number, from_date, to_date)
        
        # Calculate total distance
        distance_km = cartrack.calculate_total_distance(registration_number, from_date, to_date)
        
        # Create transfer
        transfer = investec.create_transfer(registration_number, distance_km, from_date, to_date)
        
        return {
            'trips_count': len(trips) if trips else 0,
            'distance_km': distance_km,
            'transfer_amount': transfer.amount,
            'transfer_id': transfer.id,
            'transfer_status': transfer.status
        }