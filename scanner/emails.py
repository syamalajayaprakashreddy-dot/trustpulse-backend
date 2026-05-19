from django.core.mail import send_mail
from django.conf import settings

def send_scan_complete_email(user, url, result):
    if not user.email:
        return
    score = result.get('score', 0) or result.get('trust_score', 0)
    grade = result.get('grade', '')
    if score >= 70:
        icon = '✅'
        label = 'Good'
    elif score >= 40:
        icon = '⚠️'
        label = 'Moderate'
    else:
        icon = '❌'
        label = 'Poor'
    send_mail(
        subject=f'{icon} TrustPulse Scan Complete — {url} scored {score}/100',
        message=f"""Hi {user.first_name or user.username},

Your TrustPulse scan for {url} is complete!

{icon} Trust Score: {score}/100 ({label})

Log in to see your full report and fix recommendations:
https://trustpulse-frontend.vercel.app

— TrustPulse Team""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
