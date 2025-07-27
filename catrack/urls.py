from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'car-registrations', views.CarRegistrationViewSet)
router.register(r'trips', views.TripViewSet)
router.register(r'transfers', views.TransferViewSet)
router.register(r'accounts', views.InvestecAccountViewSet)
router.register(r'api-configs', views.APIConfigurationViewSet)

app_name = 'catrack'

urlpatterns = [
    path('api/', include(router.urls)),
]