from django.urls import path
from . import views
from .webhook import stripe_webhook
from .scan_views import scan_history, google_auth

urlpatterns = [
    # existing
    path("scan/",             views.scan_website,         name="scan"),
    path("compare/",          views.compare_competitors,  name="compare"),
    path("alert/",            views.save_email_alert,     name="alert"),
    path("validate-code/",    views.validate_code,        name="validate_code"),
    path("health/",           views.health_check,         name="health"),
    path("webhook/stripe/",   stripe_webhook,             name="stripe_webhook"),
    path("test-email/",       views.test_email,           name="test_email"),

    # ✅ NEW: scan history
    path("scans/",            scan_history,               name="scan_history"),
]
