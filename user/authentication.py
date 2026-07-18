from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from django.utils import timezone
from datetime import timedelta

class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Custom Token Authentication backend that enforces a 6-hour Token TTL.
    Expired tokens are automatically removed from the database when used,
    forcing the user to re-authenticate.
    """
    TOKEN_TTL_HOURS = 6

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed("Noto'g'ri yoki yaroqsiz token.")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("Foydalanuvchi faol emas.")

        if hasattr(token.user, 'xodim') and not token.user.xodim.is_active:
            raise exceptions.AuthenticationFailed("Ushbu xodim faol emas.")

        # Check if the token has expired (MED-2: TTL = 6 hours)
        utc_now = timezone.now()
        if token.created < utc_now - timedelta(hours=self.TOKEN_TTL_HOURS):
            token.delete()
            raise exceptions.AuthenticationFailed("Token muddati tugagan. Qaytadan tizimga kiring.")

        return (token.user, token)
