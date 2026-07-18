import sys
from rest_framework.throttling import SimpleRateThrottle

class BypassTestThrottleMixin:
    def allow_request(self, request, view):
        if 'test' in sys.argv:
            return True
        return super().allow_request(request, view)

class PhoneRateThrottle(BypassTestThrottleMixin, SimpleRateThrottle):
    """
    Limits the number of login attempts to any specific phone number globally.
    This protects against distributed brute-force attacks where attackers target
    a single account using multiple different IP addresses.
    """
    scope = 'phone'
    rate = '5/minute'

    def get_cache_key(self, request, view):
        if request.method != 'POST':
            return None

        telefon_raqam = request.data.get('telefon_raqam')
        if not telefon_raqam:
            return None

        # Standardize the phone format to build a consistent cache key
        ident = str(telefon_raqam).strip().replace('+', '')
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class IPLoginRateThrottle(BypassTestThrottleMixin, SimpleRateThrottle):
    """
    Limits login POST requests from a single IP to prevent brute-forcing.
    Does not throttle GET requests, letting developers/users refresh the page safely.
    """
    scope = 'login'
    rate = '5/minute'

    def get_cache_key(self, request, view):
        if request.method != 'POST':
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }

