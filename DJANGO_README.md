# Django API Setup for CarTrack to Investec

This document describes the Django API and admin interface setup for the CarTrack to Investec integration.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py migrate
```

### 3. Create Superuser
```bash
python manage.py createsuperuser
```

### 4. Start Development Server
```bash
python manage.py runserver
```

## Admin Interface

Access the Django admin interface at: `http://localhost:8000/admin/`

The admin interface provides management for:

- **Car Registrations** - Manage vehicle registrations and per-km rates
- **API Configurations** - Store CarTrack and Investec API credentials
- **Investec Accounts** - Manage from/to account details
- **Trips** - View imported trip data from CarTrack
- **Transfers** - View and manage money transfers

## API Endpoints

Base API URL: `http://localhost:8000/api/`

### Available Endpoints:

- `GET /api/car-registrations/` - List all car registrations
- `POST /api/car-registrations/` - Create new car registration
- `GET /api/trips/` - List all trips (supports filtering)
- `GET /api/transfers/` - List all transfers
- `POST /api/transfers/process_distance_transfer/` - Process distance calculation and transfer
- `GET /api/transfers/summary/` - Get transfer statistics
- `GET /api/accounts/` - List Investec accounts
- `GET /api/api-configs/` - List API configurations

### Query Parameters:

**Trips endpoint supports filtering:**
- `?car_registration=DV77FCGP` - Filter by registration
- `?start_date=2023-01-01` - Filter by start date
- `?end_date=2023-12-31` - Filter by end date

## Process Distance Transfer

To process a distance transfer via API:

```bash
POST /api/transfers/process_distance_transfer/
Content-Type: application/json

{
    "registration_number": "DV77FCGP",
    "from_date": "2023-01-01", 
    "to_date": "2023-01-31"
}
```

This will:
1. Fetch trip data from CarTrack API
2. Calculate total distance
3. Create transfer in Investec
4. Store all data in the database

## Configuration

Before using the integration, configure:

1. **API Configuration** (via admin):
   - CarTrack username and API key
   - Investec client ID, secret key, and API key

2. **Car Registrations** (via admin):
   - Add vehicle registration numbers
   - Set per-km rates

3. **Investec Accounts** (via admin):
   - Configure from/to accounts for transfers

## Original Lambda Function

The original Lambda function code remains in `service.py` and is wrapped by Django services in `catrack/services.py`.