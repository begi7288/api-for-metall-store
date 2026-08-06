import os

class RequestDebugLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            os.makedirs(r"c:\Temir Dokon\temirdokon_v1\scratch", exist_ok=True)
            with open(r"c:\Temir Dokon\temirdokon_v1\scratch\login_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\nIncoming Request: {request.method} {request.path}\n")
        except:
            pass

        response = self.get_response(request)

        try:
            with open(r"c:\Temir Dokon\temirdokon_v1\scratch\login_debug.log", "a", encoding="utf-8") as f:
                f.write(f"Response: {response.status_code}\n")
        except:
            pass

        return response
