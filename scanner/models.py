from django.db import models
from django.contrib.auth.models import User


class ScanHistory(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scans')
    url       = models.URLField(max_length=500)
    score     = models.IntegerField(null=True, blank=True)
    grade     = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.email} — {self.url} ({self.score})"


class ProUser(models.Model):
    """Tracks which users have active Pro subscriptions."""
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pro')
    stripe_customer  = models.CharField(max_length=100, blank=True)
    stripe_sub_id    = models.CharField(max_length=100, blank=True)
    is_active        = models.BooleanField(default=True)
    plan             = models.CharField(max_length=20, default='pro')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {'Active' if self.is_active else 'Cancelled'}"

class AccessCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    plan = models.CharField(max_length=20, default='pro')
    is_active = models.BooleanField(default=True)
    used_by = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
