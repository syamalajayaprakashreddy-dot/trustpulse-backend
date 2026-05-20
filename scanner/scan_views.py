import os
import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    credential = request.data.get('credential')
    if not credential:
        return Response({'error': 'credential is required'}, status=400)
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    try:
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id, clock_skew_in_seconds=10)
    except ValueError as e:
        return Response({'error': f'Invalid Google token: {str(e)}'}, status=401)
    except Exception as e:
        return Response({'error': f'Token error: {str(e)}'}, status=500)
    email = idinfo.get('email', '').lower().strip()
    first_name = idinfo.get('given_name', '')
    last_name = idinfo.get('family_name', '')
    if not email:
        return Response({'error': 'No email in token'}, status=400)
    user, created = User.objects.get_or_create(email=email, defaults={'username': email, 'first_name': first_name, 'last_name': last_name})
    if not created:
        if not user.first_name and first_name:
            user.first_name = first_name
        if not user.last_name and last_name:
            user.last_name = last_name
        user.save()
    refresh = RefreshToken.for_user(user)
    return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user': {'email': email, 'first_name': first_name, 'last_name': last_name}})

@login_required
def scan_history(request):
    return JsonResponse({'scans': [], 'message': 'Scan history endpoint'})
