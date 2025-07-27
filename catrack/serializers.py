from rest_framework import serializers
from .models import CarRegistration, Trip, Transfer, InvestecAccount, APIConfiguration


class CarRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarRegistration
        fields = '__all__'


class TripSerializer(serializers.ModelSerializer):
    car_registration_number = serializers.CharField(source='car_registration.registration_number', read_only=True)
    distance_km = serializers.ReadOnlyField()
    
    class Meta:
        model = Trip
        fields = '__all__'


class InvestecAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestecAccount
        fields = '__all__'


class TransferSerializer(serializers.ModelSerializer):
    car_registration_number = serializers.CharField(source='car_registration.registration_number', read_only=True)
    from_account_name = serializers.CharField(source='from_account.account_name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.account_name', read_only=True)
    
    class Meta:
        model = Transfer
        fields = '__all__'


class APIConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIConfiguration
        fields = '__all__'
        extra_kwargs = {
            'secret_key': {'write_only': True},
            'api_key': {'write_only': True},
            'password': {'write_only': True},
        }