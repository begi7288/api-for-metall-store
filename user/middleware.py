import os
from django.conf import settings

class RequestDebugLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            log_dir = os.path.join(settings.BASE_DIR, "scratch")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "login_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"\nIncoming Request: {request.method} {request.path}\n")
        except:
            pass

        response = self.get_response(request)

        try:
            log_dir = os.path.join(settings.BASE_DIR, "scratch")
            with open(os.path.join(log_dir, "login_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"Response: {response.status_code}\n")
        except:
            pass

        return response
