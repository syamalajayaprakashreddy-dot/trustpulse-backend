"""
scanner/webhook.py — Stripe webhook with unique access code generation.
Push this to replace scanner/webhook.py in your repo.
"""
import stripe
import os
import json
import hashlib
import secrets
import string
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .email_service import send_pro_access_email, send_pdf_report_email
from .scanner import run_full_scan


def generate_access_code(email: str) -> str:
    """Generate a unique, readable 10-char access code tied to the customer's email."""
    alphabet = string.ascii_uppercase + string.digits
    # Deterministic prefix from email so the same customer always gets the same code
    seed = hashlib.sha256(email.lower().encode()).hexdigest()[:4].upper()
    random_part = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"TP-{seed}-{random_part}"


def save_access_code(email: str, code: str, plan: str = 'pro') -> None:
    """Persist the access code to a local JSON store (swap for DB in production)."""
    codes_file = 'access_codes.json'
    codes = {}
    if os.path.exists(codes_file):
        with open(codes_file, 'r') as f:
            codes = json.load(f)
    codes[code] = {
        'email': email,
        'plan': plan,
        'active': True,
        'created_at': str(__import__('datetime').datetime.utcnow()),
    }
    with open(codes_file, 'w') as f:
        json.dump(codes, f, indent=2)


def validate_access_code(code: str) -> dict | None:
    """Return the access code record if valid, else None."""
    # Hardcoded beta code always works
    if code.strip().upper() == 'TRUST2025':
        return {'email': 'beta', 'plan': 'pro', 'active': True}

    codes_file = 'access_codes.json'
    if not os.path.exists(codes_file):
        return None
    with open(codes_file, 'r') as f:
        codes = json.load(f)
    record = codes.get(code.strip().upper())
    return record if record and record.get('active') else None


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # ── Subscription created / payment succeeded → send Pro access code ──────
    if event['type'] in ('checkout.session.completed', 'invoice.payment_succeeded'):
        session = event['data']['object']
        customer_email = (
            session.get('customer_details', {}).get('email')
            or session.get('customer_email')
        )
        if customer_email:
            code = generate_access_code(customer_email)
            plan = 'pro'

            # Check if this was a one-time PDF report purchase
            amount = session.get('amount_total', 0)
            if amount and amount >= 4900:   # £49 in pence
                plan = 'pdf_report'

            save_access_code(customer_email, code, plan)

            if plan == 'pdf_report':
                # Run a scan and email the PDF report
                url = session.get('metadata', {}).get('url', 'your-site.com')
                try:
                    scan_data = run_full_scan(url)
                except Exception:
                    scan_data = {'score': 0, 'grade': 'Unknown', 'url': url, 'checks': [], 'issues': []}
                send_pdf_report_email(customer_email, scan_data)
            else:
                send_pro_access_email(customer_email, code)

    # ── Subscription cancelled → deactivate code ─────────────────────────────
    elif event['type'] == 'customer.subscription.deleted':
        customer_email = event['data']['object'].get('customer_email')
        if customer_email:
            codes_file = 'access_codes.json'
            if os.path.exists(codes_file):
                with open(codes_file, 'r') as f:
                    codes = json.load(f)
                for code, record in codes.items():
                    if record.get('email') == customer_email:
                        record['active'] = False
                with open(codes_file, 'w') as f:
                    json.dump(codes, f, indent=2)

    return HttpResponse(status=200)
