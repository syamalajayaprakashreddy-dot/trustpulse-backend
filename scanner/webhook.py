import os
import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import ProUser


def get_or_create_pro_user(email, stripe_customer='', stripe_sub_id='', plan='pro'):
    """Find user by email and mark as Pro."""
    try:
        user = User.objects.get(email=email)
        pro, created = ProUser.objects.update_or_create(
            user=user,
            defaults={
                'stripe_customer': stripe_customer,
                'stripe_sub_id': stripe_sub_id,
                'is_active': True,
                'plan': plan,
            }
        )
        return user, pro
    except User.DoesNotExist:
        return None, None


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # ── Payment succeeded ────────────────────────────────────────────────────
    if event['type'] in ('checkout.session.completed', 'invoice.payment_succeeded'):
        session = event['data']['object']
        customer_email = (
            session.get('customer_details', {}).get('email')
            or session.get('customer_email')
        )
        customer_id = session.get('customer', '')
        sub_id = session.get('subscription', '')
        amount = session.get('amount_total', 0)

        if customer_email:
            plan = 'pdf_report' if (amount and amount >= 4900) else 'pro'

            # Mark user as Pro in DB
            user, pro = get_or_create_pro_user(
                customer_email,
                stripe_customer=customer_id,
                stripe_sub_id=sub_id or '',
                plan=plan,
            )

            # Send access email (existing function)
            try:
                from .webhook_email import send_pro_access_email, generate_access_code, save_access_code
                code = generate_access_code(customer_email)
                save_access_code(customer_email, code, plan)
                if plan == 'pdf_report':
                    url = session.get('metadata', {}).get('url', 'your-site.com')
                    try:
                        from .scanner import run_full_scan
                        scan_data = run_full_scan(url)
                    except Exception:
                        scan_data = {'score': 0, 'grade': 'Unknown', 'url': url, 'checks': [], 'issues': []}
                    from .webhook_email import send_pdf_report_email
                    send_pdf_report_email(customer_email, scan_data)
                else:
                    send_pro_access_email(customer_email, code)
            except Exception:
                pass  # Email failure shouldn't break webhook

    # ── Subscription cancelled ───────────────────────────────────────────────
    elif event['type'] == 'customer.subscription.deleted':
        obj = event['data']['object']
        customer_id = obj.get('customer', '')
        try:
            pro = ProUser.objects.get(stripe_customer=customer_id)
            pro.is_active = False
            pro.save()
        except ProUser.DoesNotExist:
            pass

    return HttpResponse(status=200)
