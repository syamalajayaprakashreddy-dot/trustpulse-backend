import stripe
import os
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .scanner import run_full_scan, fetch_page
from .email_service import send_pdf_report_email


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
    Body: { "url": "https://mysite.com", "competitors": ["https://comp1.com"] }
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
    """
    email = request.data.get('email', '').strip()
    url = request.data.get('url', '').strip()
    threshold = request.data.get('threshold', 70)
    if not email or not url:
        return Response(
            {'error': 'Email and URL are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    alerts_file = 'alerts.json'
    alerts = []
    if os.path.exists(alerts_file):
        with open(alerts_file, 'r') as f:
            alerts = json.load(f)
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


@csrf_exempt
def stripe_webhook(request):
    """
    POST /api/webhook/
    Handles Stripe payment confirmation and sends email
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email')
        if customer_email:
            scan_data = {
                'score': 85,
                'grade': 'High Trust',
                'url': 'your-site.com',
                'checks': [],
                'issues': []
            }
            send_pdf_report_email(customer_email, scan_data)

    return HttpResponse(status=200)


@api_view(['GET'])
def test_email(request):
    from .email_service import send_pro_access_email
    result = send_pro_access_email('syamalajayaprakashreddy@gmail.com')
    if result:
        return Response({'status': 'Email sent! Check your Gmail inbox.'})
    return Response({'status': 'Email failed — check SendGrid key.'})

@api_view(['POST'])
def debug_fetch(request):
    url = request.data.get('url', '')
    html, soup = fetch_page(url)
    if html:
        return Response({'html_preview': html[:2000], 'length': len(html)})
    return Response({'error': 'Could not fetch'})
