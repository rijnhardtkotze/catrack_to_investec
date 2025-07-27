from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta

from .models import CarRegistration, Trip, Transfer, InvestecAccount, APIConfiguration
from .serializers import (
    CarRegistrationSerializer, TripSerializer, TransferSerializer,
    InvestecAccountSerializer, APIConfigurationSerializer
)
from .services import CarTrackToInvestecService


class CarRegistrationViewSet(viewsets.ModelViewSet):
    queryset = CarRegistration.objects.all()
    serializer_class = CarRegistrationSerializer
    permission_classes = [IsAuthenticated]


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Trip.objects.all()
        car_reg = self.request.query_params.get('car_registration', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if car_reg is not None:
            queryset = queryset.filter(car_registration__registration_number=car_reg)
        if start_date is not None:
            queryset = queryset.filter(start_timestamp__date__gte=start_date)
        if end_date is not None:
            queryset = queryset.filter(start_timestamp__date__lte=end_date)
            
        return queryset


class TransferViewSet(viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def process_distance_transfer(self, request):
        """API endpoint to process distance calculation and transfer"""
        registration_number = request.data.get('registration_number')
        from_date = request.data.get('from_date')
        to_date = request.data.get('to_date')
        
        if not all([registration_number, from_date, to_date]):
            return Response(
                {'error': 'registration_number, from_date, and to_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = CarTrackToInvestecService()
            result = service.process_distance_transfer(registration_number, from_date, to_date)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transfer summary statistics"""
        transfers = Transfer.objects.all()
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            transfers = transfers.filter(transfer_date__gte=start_date)
        if end_date:
            transfers = transfers.filter(transfer_date__lte=end_date)
        
        total_amount = sum(t.amount for t in transfers)
        total_distance = sum(t.distance_km for t in transfers)
        
        return Response({
            'total_transfers': transfers.count(),
            'total_amount': total_amount,
            'total_distance_km': total_distance,
            'completed_transfers': transfers.filter(status='completed').count(),
            'pending_transfers': transfers.filter(status='pending').count(),
            'failed_transfers': transfers.filter(status='failed').count(),
        })


class InvestecAccountViewSet(viewsets.ModelViewSet):
    queryset = InvestecAccount.objects.all()
    serializer_class = InvestecAccountSerializer
    permission_classes = [IsAuthenticated]


class APIConfigurationViewSet(viewsets.ModelViewSet):
    queryset = APIConfiguration.objects.all()
    serializer_class = APIConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """Override list to hide sensitive data"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Remove sensitive fields from response
            for item in serializer.data:
                item.pop('secret_key', None)
                item.pop('api_key', None)
                item.pop('password', None)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        for item in serializer.data:
            item.pop('secret_key', None)
            item.pop('api_key', None)
            item.pop('password', None)
        return Response(serializer.data)
