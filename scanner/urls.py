"""
scanner/urls.py — updated to include /api/validate-code/ endpoint.
Push this to replace scanner/urls.py in your repo.
"""
from django.urls import path
from . import views
from .webhook import stripe_webhook

urlpatterns = [
    path('api/scan/',           views.scan_website,      name='scan'),
    path('api/compare/',        views.compare_competitors,name='compare'),
    path('api/alert/',          views.save_email_alert,  name='alert'),
    path('api/validate-code/',  views.validate_code,     name='validate_code'),
    path('api/health/',         views.health_check,      name='health'),
    path('api/webhook/stripe/', stripe_webhook,           name='stripe_webhook'),
    path('api/test-email/',     views.test_email,        name='test_email'),
]
