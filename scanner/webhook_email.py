import os
import random
import string
import requests
from datetime import datetime


def generate_access_code(email=''):
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    return f"TP-{part1}-{part2}"


def save_access_code(email, code, plan='pro'):
    try:
        from scanner.models import AccessCode
        AccessCode.objects.get_or_create(
            code=code,
            defaults={'plan': plan, 'is_active': True}
        )
        return True
    except Exception as e:
        print(f"Error saving: {e}")
        return False


def validate_access_code(code):
    try:
        from scanner.models import AccessCode
        return AccessCode.objects.get(code=code.strip().upper(), is_active=True)
    except Exception:
        return None


def send_pro_access_email(customer_email, code):
    sendgrid_key = os.environ.get('SENDGRID_API_KEY', '')
    from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'hello@trustpulse.ai')
    if not sendgrid_key:
        print(f"No SendGrid key — code for {customer_email}: {code}")
        return False
    payload = {
        'personalizations': [{'to': [{'email': customer_email}]}],
        'from': {'email': from_email, 'name': 'TrustPulse'},
        'subject': f'Your TrustPulse Pro Access Code: {code}',
        'content': [{'type': 'text/html', 'value': f'<h2>Your Pro Code: <strong>{code}</strong></h2><p>Go to <a href="https://trustpulse-frontend.vercel.app">trustpulse-frontend.vercel.app</a>, scan a site, click Unlock Pro and enter your code.</p>'}]
    }
    try:
        r = requests.post('https://api.sendgrid.com/v3/mail/send',
            headers={'Authorization': f'Bearer {sendgrid_key}', 'Content-Type': 'application/json'},
            json=payload, timeout=10)
        print(f"SendGrid response: {r.status_code}")
        return r.status_code in (200, 202)
    except Exception as e:
        print(f"Email error: {e}")
        return False
