from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from scanner.auth_views import RegisterView, UserProfileView, UpdateProfileView, ChangePasswordView, forgot_password
from scanner.scan_views import google_auth

urlpatterns = [
    path('api/', include('scanner.urls')),

    # auth
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/',    TokenObtainPairView.as_view()),
    path('api/auth/refresh/',  TokenRefreshView.as_view()),
    path('api/auth/me/',       UserProfileView.as_view()),

    # ✅ NEW: Google OAuth
    path('api/auth/google/',   google_auth),
    path('api/auth/forgot-password/', forgot_password),
]
