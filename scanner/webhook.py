import json
import stripe
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .scanner import run_full_scan
from .email_service import send_pdf_report_email, send_pro_access_email


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhooks for automatic email delivery.
    Set up webhook in Stripe Dashboard → Developers → Webhooks
    Add endpoint: https://web-production-63792.up.railway.app/api/webhook/
    Events to listen: checkout.session.completed
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

    # Verify webhook signature
    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except Exception as e:
            return HttpResponse(status=400)
    else:
        try:
            event = json.loads(payload)
        except Exception:
            return HttpResponse(status=400)

    # Handle payment completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email', '')
        amount = session.get('amount_total', 0)
        payment_link = session.get('payment_link', '')

        if not customer_email:
            return HttpResponse(status=200)

        # PDF Report payment (£49 = 4900 pence)
        PDF_LINK = os.environ.get('PDF_PAYMENT_LINK', 'plink_')
        PRO_LINK = os.environ.get('PRO_PAYMENT_LINK', 'plink_')

        if amount == 4900:
            # Run a scan for the customer's website
            # For now scan a default URL — in future ask URL at checkout
            try:
                scan_data = run_full_scan('https://example.com')
                send_pdf_report_email(customer_email, scan_data)
                print(f"PDF report sent to {customer_email}")
            except Exception as e:
                print(f"Error sending PDF: {e}")

        elif amount == 1900:
            # Pro subscription
            try:
                send_pro_access_email(customer_email)
                print(f"Pro access code sent to {customer_email}")
            except Exception as e:
                print(f"Error sending Pro code: {e}")

    return HttpResponse(status=200)