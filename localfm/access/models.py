from django.contrib.auth.models import User
from django.db import models
from django.db.models import ForeignKey


class ApiKey(models.Model):
    user = ForeignKey(User, on_delete=models.CASCADE, related_name="keys")
    name = models.CharField(max_length=256)
    data = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField()
