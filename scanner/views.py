from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .scanner import run_full_scan


@api_view(['POST'])
def scan_website(request):
    """
    POST /api/scan/
    Body: { "url": "https://example.com" }
    Returns: full trust scan report
    """
    url = request.data.get('url', '').strip()

    if not url:
        return Response(
            {'error': 'Please provide a URL to scan.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Basic URL sanity check
    if len(url) > 500:
        return Response(
            {'error': 'URL is too long.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = run_full_scan(url)
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Scan failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    """GET /api/health/ — confirms the API is running."""
    return Response({'status': 'TrustPulse API is running ✓'})


@api_view(['POST'])
def compare_competitors(request):
    """
    POST /api/compare/
    Body: { "url": "https://mysite.com", "competitors": ["https://comp1.com", "https://comp2.com"] }
    Returns: comparison data with scores and insights
    """
    url = request.data.get('url', '').strip()
    competitors = request.data.get('competitors', [])

    if not url:
        return Response(
            {'error': 'Please provide your website URL.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from .competitor import run_competitor_comparison
        result = run_competitor_comparison(url, competitors)
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Comparison failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def save_email_alert(request):
    """
    POST /api/alerts/
    Body: { "email": "user@example.com", "url": "https://mysite.com", "threshold": 70 }
    Saves email alert preference (stored simply for now)
    """
    email = request.data.get('email', '').strip()
    url = request.data.get('url', '').strip()
    threshold = request.data.get('threshold', 70)

    if not email or not url:
        return Response(
            {'error': 'Email and URL are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Store alert (simple file-based for now)
    import json, os
    alerts_file = 'alerts.json'
    alerts = []
    if os.path.exists(alerts_file):
        with open(alerts_file, 'r') as f:
            alerts = json.load(f)

    # Remove existing alert for same email+url
    alerts = [a for a in alerts if not (a['email'] == email and a['url'] == url)]

    alerts.append({
        'email': email,
        'url': url,
        'threshold': threshold,
        'active': True
    })

    with open(alerts_file, 'w') as f:
        json.dump(alerts, f)

    return Response({
        'success': True,
        'message': f'Alert set! We will email {email} when {url} trust score drops below {threshold}.'
    }, status=status.HTTP_200_OK)