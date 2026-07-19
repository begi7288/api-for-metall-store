from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        "message": "TemirDokon API is running",
        "endpoints": {
            "auth": {
                "register": "/users/register/",
                "login": "/users/login/",
                "logout": "/users/logout/",
                "me": "/users/me/",
                "change-password": "/users/change-password/"
            },
            "products": "/products/",
            "orders": "/products/order/"
        }
    })
