from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from .models import ApiKey


class ApiKeyAuthBackend(BaseBackend):
    def get_user(self, user_id):
        return User.objects.get(pk=user_id)

    def authenticate(self, request, api_key=None, **kwargs):
        found_data = ApiKey.objects.filter(name__exact=api_key).first()
        return found_data.user if found_data else None
