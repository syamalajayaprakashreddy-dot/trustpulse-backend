import requests as http_requests
from django.contrib.auth.models import User
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ScanHistory


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def scan_history(request):
    if request.method == 'GET':
        scans = ScanHistory.objects.filter(user=request.user)[:20]
        data = [{'id': s.id, 'url': s.url, 'score': s.score, 'grade': s.grade, 'timestamp': s.timestamp.isoformat()} for s in scans]
        return Response(data)
    url = request.data.get('url') or request.data.get('brand_url', '')
    score = request.data.get('score')
    grade = request.data.get('grade', '')
    if not url:
        return Response({'error': 'url is required'}, status=400)
    scan, created = ScanHistory.objects.update_or_create(
        user=request.user, url=url,
        defaults={'score': score, 'grade': grade},
    )
    return Response({'id': scan.id, 'url': scan.url, 'score': scan.score, 'grade': scan.grade, 'timestamp': scan.timestamp.isoformat()}, status=201 if created else 200)


@api_view(['POST'])
def google_auth(request):
    credential = request.data.get('credential')
    if not credential:
        return Response({'error': 'credential is required'}, status=400)
    try:
        resp = http_requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': credential}, timeout=10)
        if resp.status_code != 200:
            return Response({'error': 'Invalid Google token'}, status=401)
        payload = resp.json()
    except Exception:
        return Response({'error': 'Could not verify Google token'}, status=500)
    email = payload.get('email')
    name = payload.get('name', '')
    first_name = payload.get('given_name', name.split()[0] if name else '')
    last_name = payload.get('family_name', '')
    if not email:
        return Response({'error': 'Could not get email from Google'}, status=400)
    user, created = User.objects.get_or_create(username=email, defaults={'email': email, 'first_name': first_name, 'last_name': last_name})
    if not created:
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])
    refresh = RefreshToken.for_user(user)
    return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user': {'email': email, 'name': name or first_name}})
