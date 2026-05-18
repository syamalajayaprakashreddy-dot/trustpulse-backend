"""
trustpulse/settings.py — production-ready settings
Push this to replace trustpulse/settings.py in your repo.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-insecure-key-change-in-prod')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost', '127.0.0.1',
    'web-production-b87c1.up.railway.app',
    'web-production-4592c.up.railway.app',
    os.environ.get('RAILWAY_PUBLIC_DOMAIN', ''),
    os.environ.get('CUSTOM_DOMAIN', ''),
]

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'corsheaders',
    'scanner',
    'rest_framework_simplejwt',
    'social_django',
    'django.contrib.sessions',
]

# ---- JWT Auth ----
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # ← must be FIRST
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'trustpulse.urls'
WSGI_APPLICATION = 'trustpulse.wsgi.application'

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Allows the frontend (wherever hosted) to call the API.
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = ["https://trustpulse-frontend.vercel.app"]          # open during beta — restrict after launch
CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent', 'x-requested-with',
]

# ─── Database ────────────────────────────────────────────────────────────────
# SQLite for now; swap for postgres via DATABASE_URL on Railway
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ─── Cache ───────────────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 60 * 60 * 24,   # 24 hours
    }
}

# ─── Stripe ───────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY      = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET  = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRO_PRICE_ID    = os.environ.get('STRIPE_PRO_PRICE_ID', '')

# ─── SendGrid ────────────────────────────────────────────────────────────────
SENDGRID_API_KEY       = os.environ.get('SENDGRID_API_KEY', '')
FROM_EMAIL             = os.environ.get('FROM_EMAIL', 'hello@trustpulse.ai')

# ─── Misc ─────────────────────────────────────────────────────────────────────
LANGUAGE_CODE   = 'en-gb'
TIME_ZONE       = 'Europe/London'
USE_I18N        = True
USE_TZ          = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
