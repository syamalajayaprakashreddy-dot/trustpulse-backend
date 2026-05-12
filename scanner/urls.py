from django.urls import path
from . import views
from . import webhook

urlpatterns = [
    path('scan/', views.scan_website, name='scan_website'),
    path('health/', views.health_check, name='health_check'),
    path('compare/', views.compare_competitors, name='compare_competitors'),
    path('alerts/', views.save_email_alert, name='save_email_alert'),
    path('webhook/', webhook.stripe_webhook, name='stripe_webhook'),
    path('test-email/', views.test_email, name='test_email'),
]