"""
scanner/views.py — updated with dynamic access code validation.
Push this to replace scanner/views.py in your repo.
"""
import os
import json
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache

from .scanner import run_full_scan, fetch_page
from .email_service import send_pdf_report_email, send_pro_access_email
from .webhook_email import validate_access_code


@api_view(['POST'])
def scan_website(request):
    url = request.data.get('url', '').strip()
    if not url:
        return Response({'error': 'Please provide a URL to scan.'}, status=400)
    if len(url) > 500:
        return Response({'error': 'URL is too long.'}, status=400)
    try:
        cache_key = 'scan_' + hashlib.md5(url.lower().encode()).hexdigest()
        cached = cache.get(cache_key)
        if cached:
            cached['cached'] = True
            return Response(cached)
        result = run_full_scan(url)
        result["cached"] = False

        # ── Save to ScanHistory DB ──────────────────────────────────────────
        if request.user.is_authenticated:
            try:
                from .models import ScanHistory
                ScanHistory.objects.create(
                    user=request.user,
                    url=url,
                    score=result.get('trust_score') or result.get('score') or 0,
                    grade=result.get('grade', ''),
                )
            except Exception as db_err:
                print(f"DB SAVE ERROR: {db_err}")

        # ── Send email notification ─────────────────────────────────────────
        try:
            from .email_service import send_scan_complete_email, send_pro_access_email
            if request.user.is_authenticated:
                send_scan_complete_email(request.user, url, result)
        except Exception as email_err:
            print(f"EMAIL ERROR: {email_err}")

        cache.set(cache_key, result, 60 * 60 * 24)
        return Response(result)
    except Exception as e:
        return Response({'error': f'Scan failed: {str(e)}'}, status=500)


@api_view(['POST'])
def validate_code(request):
    """
    Validates a Pro access code.
    POST { "code": "TP-XXXX-YYYYYY" }
    Returns { "valid": true, "plan": "pro" } or { "valid": false }
    """
    code = request.data.get('code', '').strip().upper()
    if not code:
        return Response({'valid': False, 'error': 'No code provided.'}, status=400)
    record = validate_access_code(code)
    if record:
        return Response({'valid': True, 'plan': record.get('plan', 'pro')})
    return Response({'valid': False, 'error': 'Invalid or inactive code.'}, status=401)


@api_view(['POST'])
def save_email_alert(request):
    email     = request.data.get('email', '').strip()
    url       = request.data.get('url', '').strip()
    threshold = request.data.get('threshold', 70)
    if not email or not url:
        return Response({'error': 'Email and URL are required.'}, status=400)

    alerts_file = 'alerts.json'
    alerts = []
    if os.path.exists(alerts_file):
        with open(alerts_file, 'r') as f:
            alerts = json.load(f)
    # Upsert
    alerts = [a for a in alerts if not (a['email'] == email and a['url'] == url)]
    alerts.append({'email': email, 'url': url, 'threshold': threshold, 'active': True})
    with open(alerts_file, 'w') as f:
        json.dump(alerts, f)

    return Response({
        'success': True,
        'message': f'Alert set! We will email {email} when {url} drops below {threshold}.'
    })


@api_view(['POST'])
def compare_competitors(request):
    url         = request.data.get('url', '').strip()
    competitors = request.data.get('competitors', [])
    if not url:
        return Response({'error': 'Please provide your website URL.'}, status=400)
    try:
        from .competitor import run_competitor_comparison
        result = run_competitor_comparison(url, competitors)
        return Response(result)
    except Exception as e:
        return Response({'error': f'Comparison failed: {str(e)}'}, status=500)


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'TrustPulse API is running ✓', 'version': '2.0'})


@api_view(['GET'])
def test_email(request):
    result = send_pro_access_email('test@example.com', 'TRUST2025')
    return Response({'status': 'sent' if result else 'failed'})


@api_view(['POST'])
def check_alerts(request):
    """Called by a cron job to check all alerts and send emails"""
    import json, os
    from .scanner import run_scan
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    alerts_file = 'alerts.json'
    if not os.path.exists(alerts_file):
        return Response({'message': 'No alerts'})

    with open(alerts_file, 'r') as f:
        alerts = json.load(f)

    sent = 0
    for alert in alerts:
        if not alert.get('active'):
            continue
        try:
            result = run_scan(alert['url'])
            score = result.get('trust_score', 0)
            threshold = alert.get('threshold', 70)
            prev_score = alert.get('last_score', score)

            if score != prev_score:
                # Score changed — send alert email
                sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                direction = '📈 improved' if score > prev_score else '📉 dropped'
                message = Mail(
                    from_email=os.environ.get('FROM_EMAIL', 'hello@trustpulse.ai'),
                    to_emails=alert['email'],
                    subject=f'TrustPulse Alert: {alert["url"]} score {direction}',
                    html_content=f'''
                    <h2>Trust Score Alert</h2>
                    <p>The trust score for <strong>{alert["url"]}</strong> has changed:</p>
                    <p>Previous score: <strong>{prev_score}</strong></p>
                    <p>New score: <strong>{score}</strong></p>
                    <p>Status: Score {direction}</p>
                    <a href="https://trustpulse-frontend.vercel.app">View full report</a>
                    '''
                )
                sg.send(message)
                alert['last_score'] = score
                sent += 1
        except Exception as e:
            continue

    with open(alerts_file, 'w') as f:
        json.dump(alerts, f)

    return Response({'message': f'Checked {len(alerts)} alerts, sent {sent} emails'})

@csrf_exempt
def ai_fix_recommendations(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    import anthropic, json as j
    data = j.loads(request.body)
    prompt = data.get('prompt', '')
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return JsonResponse({'content': [{'text': msg.content[0].text}]})
