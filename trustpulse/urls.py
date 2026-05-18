from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from scanner.auth_views import RegisterView, UserProfileView

urlpatterns = [
    path('api/', include('scanner.urls')),
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', TokenObtainPairView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/auth/me/', UserProfileView.as_view()),
]
