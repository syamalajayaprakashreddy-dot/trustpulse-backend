import requests as http_requests
from django.contrib.auth.models import User
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ScanHistory


# ─── Scan History ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def scan_history(request):
    """
    GET  /api/scans/  — return the logged-in user's last 20 scans
    POST /api/scans/  — save a new scan result
    """
    if request.method == 'GET':
        scans = ScanHistory.objects.filter(user=request.user)[:20]
        data = [
            {
                'id':        s.id,
                'url':       s.url,
                'score':     s.score,
                'grade':     s.grade,
                'timestamp': s.timestamp.isoformat(),
            }
            for s in scans
        ]
        return Response(data)

    # POST — save scan
    url   = request.data.get('url') or request.data.get('brand_url', '')
    score = request.data.get('score')
    grade = request.data.get('grade', '')

    if not url:
        return Response({'error': 'url is required'}, status=400)

    scan = ScanHistory.objects.create(
        user=request.user,
        url=url,
        score=score,
        grade=grade,
    )
    return Response({
        'id':        scan.id,
        'url':       scan.url,
        'score':     scan.score,
        'grade':     scan.grade,
        'timestamp': scan.timestamp.isoformat(),
    }, status=201)


# ─── Google OAuth ──────────────────────────────────────────────────────────────

@api_view(['POST'])
def google_auth(request):
    """
    POST /api/auth/google/
    Body: { "credential": "<Google ID token>" }
    Returns: { "access": "...", "refresh": "...", "user": {...} }

    Flow:
    1. Receive the Google ID token from the frontend
    2. Verify it with Google's tokeninfo endpoint
    3. Find or create the Django user
    4. Return JWT tokens
    """
    credential = request.data.get('credential')
    if not credential:
        return Response({'error': 'credential is required'}, status=400)

    # Verify token with Google
    try:
        resp = http_requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': credential},
            timeout=10,
        )
        if resp.status_code != 200:
            return Response({'error': 'Invalid Google token'}, status=401)

        payload = resp.json()
    except Exception:
        return Response({'error': 'Could not verify Google token'}, status=500)

    email      = payload.get('email')
    name       = payload.get('name', '')
    first_name = payload.get('given_name', name.split()[0] if name else '')
    last_name  = payload.get('family_name', '')

    if not email:
        return Response({'error': 'Could not get email from Google'}, status=400)

    # Get or create user
    user, created = User.objects.get_or_create(
        username=email,
        defaults={
            'email':      email,
            'first_name': first_name,
            'last_name':  last_name,
        },
    )
    if not created:
        # Update name in case it changed
        user.first_name = first_name
        user.last_name  = last_name
        user.save(update_fields=['first_name', 'last_name'])

    # Issue JWT
    refresh = RefreshToken.for_user(user)
    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'email': email,
            'name':  name or first_name,
        },
    })
