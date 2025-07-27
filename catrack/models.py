from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class CarRegistration(models.Model):
    """Model to store car registration details"""
    registration_number = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200, blank=True)
    rate_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=0.25)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.registration_number


class Trip(models.Model):
    """Model to store trip data from CarTrack API"""
    car_registration = models.ForeignKey(CarRegistration, on_delete=models.CASCADE, related_name='trips')
    trip_distance = models.IntegerField()  # Distance in meters
    start_timestamp = models.DateTimeField()
    end_timestamp = models.DateTimeField()
    raw_data = models.JSONField()  # Store original API response
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_timestamp']
    
    def __str__(self):
        return f"{self.car_registration.registration_number} - {self.trip_distance}m on {self.start_timestamp}"
    
    @property
    def distance_km(self):
        return self.trip_distance / 1000.0


class InvestecAccount(models.Model):
    """Model to store Investec account details"""
    account_id = models.CharField(max_length=100, unique=True)
    account_name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=50, choices=[
        ('from', 'From Account'),
        ('to', 'To Account'),
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.account_name} ({self.account_type})"


class Transfer(models.Model):
    """Model to store transfer history"""
    from_account = models.ForeignKey(InvestecAccount, on_delete=models.CASCADE, related_name='transfers_from')
    to_account = models.ForeignKey(InvestecAccount, on_delete=models.CASCADE, related_name='transfers_to')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    rate_per_km = models.DecimalField(max_digits=5, decimal_places=2)
    from_reference = models.CharField(max_length=100)
    to_reference = models.CharField(max_length=100)
    transfer_date = models.DateField()
    car_registration = models.ForeignKey(CarRegistration, on_delete=models.CASCADE, related_name='transfers')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"R{self.amount} transfer for {self.distance_km}km on {self.transfer_date}"


class APIConfiguration(models.Model):
    """Model to store API configuration settings"""
    name = models.CharField(max_length=50, unique=True)
    api_type = models.CharField(max_length=20, choices=[
        ('investec', 'Investec'),
        ('cartrack', 'CarTrack'),
    ])
    client_id = models.CharField(max_length=200, blank=True)
    secret_key = models.CharField(max_length=200, blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=200, blank=True)  # Stores hashed password
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Hash password if it's not already hashed and not empty
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    
    def check_password(self, raw_password):
        """Check if the raw password matches the stored hashed password"""
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return f"{self.api_type.title()} - {self.name}"
