"""
Services module that wraps the original service.py functionality
"""
import sys
import os
from datetime import datetime
from decimal import Decimal

# Add the project root to Python path to import service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import service

from .models import APIConfiguration, Trip, Transfer, CarRegistration, InvestecAccount


class CarTrackService:
    """Service class to handle CarTrack API interactions"""
    
    def __init__(self):
        config = APIConfiguration.objects.filter(api_type='cartrack', is_active=True).first()
        if not config:
            raise ValueError("No active CarTrack API configuration found")
        
        self.client = service.CarTrackAPIClient(
            username=config.username,
            api_key=config.api_key
        )
    
    def fetch_and_store_trips(self, registration_number, from_date, to_date):
        """Fetch trips from CarTrack API and store in database"""
        car_reg = CarRegistration.objects.get(registration_number=registration_number)
        
        self.client.get_trips(registration_number, from_date, to_date)
        
        if self.client.trips:
            for trip_data in self.client.trips:
                # Convert timestamps (assuming they're Unix timestamps)
                start_ts = datetime.fromtimestamp(int(trip_data.get('start_ts', 0)))
                end_ts = datetime.fromtimestamp(int(trip_data.get('end_ts', 0)))
                
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
        car_reg = CarRegistration.objects.get(registration_number=car_registration)
        
        # Calculate amount
        amount = Decimal(str(distance_km)) * car_reg.rate_per_km
        
        # Get default accounts
        from_account = InvestecAccount.objects.filter(account_type='from', is_active=True).first()
        to_account = InvestecAccount.objects.filter(account_type='to', is_active=True).first()
        
        if not from_account or not to_account:
            raise ValueError("No active from/to accounts configured")
        
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
            transfer_date=datetime.strptime(to_date, '%Y-%m-%d').date()
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
            raise e
        
        return transfer


class CarTrackToInvestecService:
    """Main service that orchestrates the CarTrack to Investec process"""
    
    def process_distance_transfer(self, registration_number, from_date, to_date):
        """Main process to calculate distance and create transfer"""
        
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