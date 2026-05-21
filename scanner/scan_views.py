import os
import json
import logging
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

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
        idinfo = id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id
        )
    except ValueError as e:
        return Response({'error': f'Invalid Google token: {str(e)}'}, status=401)
    except Exception as e:
        return Response({'error': f'Token error: {str(e)}'}, status=500)

    email = idinfo.get('email', '').lower().strip()
    first_name = idinfo.get('given_name', '')
    last_name = idinfo.get('family_name', '')
    if not email:
        return Response({'error': 'No email in token'}, status=400)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': email, 'first_name': first_name, 'last_name': last_name}
    )
    if not created:
        if not user.first_name and first_name:
            user.first_name = first_name
        if not user.last_name and last_name:
            user.last_name = last_name
        user.save()

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {'email': email, 'first_name': first_name, 'last_name': last_name}
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def scan_history(request):
    if request.method == 'POST':
        try:
            from .models import ScanHistory
            url = request.data.get('url', '').strip()
            score = request.data.get('score')
            grade = request.data.get('grade', '')
            if not url:
                return JsonResponse({'error': 'url required'}, status=400)
            scan = ScanHistory.objects.create(user=request.user, url=url, score=score, grade=grade)
            return JsonResponse({'id': scan.id, 'url': scan.url, 'score': scan.score})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    """Return the authenticated user's scan history from the database."""
    try:
        from .models import ScanHistory
        scans_qs = ScanHistory.objects.filter(user=request.user).order_by('-timestamp')[:50]
        data = [
            {
                'id': s.id,
                'url': s.url,
                'score': s.score,
                'grade': s.grade,
                'timestamp': s.timestamp.isoformat(),
            }
            for s in scans_qs
        ]
        return JsonResponse({'scans': data})
    except Exception as e:
        logger.error(f"scan_history error: {e}", exc_info=True)
        return JsonResponse({'error': str(e), 'scans': []}, status=500)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_scan(request):
    """Save a scan result for the authenticated user."""
    try:
        from .models import ScanHistory
        url = request.data.get('url', '').strip()
        score = request.data.get('score')
        grade = request.data.get('grade', '')
        if not url:
            return JsonResponse({'error': 'url is required'}, status=400)
        scan = ScanHistory.objects.create(
            user=request.user,
            url=url,
            score=score,
            grade=grade,
        )
        return JsonResponse({'id': scan.id, 'url': scan.url, 'score': scan.score, 'grade': scan.grade})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
def forgot_password(request):
    from django.contrib.auth.models import User
    email = request.data.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'error': 'email required'}, status=400)
    try:
        user = User.objects.get(email__iexact=email)
        return JsonResponse({'message': 'Reset link sent!'})
    except User.DoesNotExist:
        return JsonResponse({'error': 'Email not found'}, status=404)
