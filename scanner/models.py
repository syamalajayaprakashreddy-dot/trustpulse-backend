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
