from rest_framework.throttling import SimpleRateThrottle


class PhoneRateThrottle(SimpleRateThrottle):
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


class IPLoginRateThrottle(SimpleRateThrottle):
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


class PasswordChangeRateThrottle(SimpleRateThrottle):
    """
    LOW-3: Limits password change attempts to prevent brute-forcing old password.
    """
    scope = 'password_change'
    rate = '3/minute'

    def get_cache_key(self, request, view):
        if request.method != 'POST':
            return None
        if request.user and request.user.is_authenticated:
            return self.cache_format % {
                'scope': self.scope,
                'ident': request.user.pk
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class RegisterRateThrottle(SimpleRateThrottle):
    """
    HIGH-2: Strict rate limit on registration to prevent mass business creation.
    """
    scope = 'register'
    rate = '3/hour'

    def get_cache_key(self, request, view):
        if request.method != 'POST':
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }
