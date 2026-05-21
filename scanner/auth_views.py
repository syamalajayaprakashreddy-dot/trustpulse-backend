from django.contrib.auth.models import User
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterView(APIView):
    def post(self, request):
        email    = request.data.get('email')
        password = request.data.get('password')
        name     = request.data.get('name', '')
        if User.objects.filter(username=email).exists():
            return Response({'error': 'Email already registered'}, status=400)
        user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    {'email': email, 'name': name},
        })


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_pro = False
        try:
            is_pro = user.pro.is_active
        except Exception:
            pass
        return Response({
            'email':  user.email,
            'name':   user.first_name,
            'is_pro': is_pro,
        })


from django.contrib.auth import authenticate

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Email and password required'}, status=400)
        user = authenticate(username=email, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=401)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {'email': user.email, 'name': user.first_name}
        })


class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        user = request.user
        name = request.data.get('name')
        if name:
            user.first_name = name
            user.save()
        return Response({'email': user.email, 'name': user.first_name})


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not user.check_password(old_password):
            return Response({'error': 'Current password is incorrect'}, status=400)
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'})
