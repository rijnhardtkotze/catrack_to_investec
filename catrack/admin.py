from django.contrib import admin
from .models import CarRegistration, Trip, InvestecAccount, Transfer, APIConfiguration


@admin.register(CarRegistration)
class CarRegistrationAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'description', 'rate_per_km', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('registration_number', 'description')
    list_editable = ('rate_per_km', 'is_active')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('car_registration', 'distance_km', 'start_timestamp', 'end_timestamp', 'created_at')
    list_filter = ('car_registration', 'start_timestamp', 'created_at')
    search_fields = ('car_registration__registration_number',)
    readonly_fields = ('distance_km',)
    date_hierarchy = 'start_timestamp'
    
    def distance_km(self, obj):
        return f"{obj.distance_km:.2f} km"
    distance_km.short_description = "Distance (km)"


@admin.register(InvestecAccount)
class InvestecAccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'account_id', 'account_type', 'is_active', 'created_at')
    list_filter = ('account_type', 'is_active', 'created_at')
    search_fields = ('account_name', 'account_id')
    list_editable = ('is_active',)


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('car_registration', 'amount', 'distance_km', 'transfer_date', 'status', 'created_at')
    list_filter = ('status', 'transfer_date', 'car_registration', 'created_at')
    search_fields = ('car_registration__registration_number', 'from_reference', 'to_reference')
    readonly_fields = ('created_at',)
    date_hierarchy = 'transfer_date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('car_registration', 'from_account', 'to_account')


@admin.register(APIConfiguration)
class APIConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_type', 'is_active', 'created_at')
    list_filter = ('api_type', 'is_active', 'created_at')
    search_fields = ('name',)
    list_editable = ('is_active',)
    
    # Hide sensitive fields in list view
    fields = ('name', 'api_type', 'client_id', 'secret_key', 'api_key', 'username', 'password', 'is_active')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make password fields use password input
        if 'secret_key' in form.base_fields:
            form.base_fields['secret_key'].widget.attrs['type'] = 'password'
            form.base_fields['secret_key'].help_text = 'This field will be masked for security'
        if 'api_key' in form.base_fields:
            form.base_fields['api_key'].widget.attrs['type'] = 'password'
            form.base_fields['api_key'].help_text = 'This field will be masked for security'
        if 'password' in form.base_fields:
            form.base_fields['password'].widget.attrs['type'] = 'password'
            if obj and obj.api_type == 'cartrack':
                form.base_fields['password'].help_text = 'CarTrack passwords are stored in plaintext for API authentication'
            else:
                form.base_fields['password'].help_text = 'Passwords are automatically hashed for security'
        return form
    
    def save_model(self, request, obj, form, change):
        """Override to add logging for security-sensitive changes"""
        import logging
        logger = logging.getLogger(__name__)
        
        if change:
            logger.info(f"API Configuration '{obj.name}' updated by user '{request.user.username}'")
        else:
            logger.info(f"New API Configuration '{obj.name}' created by user '{request.user.username}'")
        
        super().save_model(request, obj, form, change)
