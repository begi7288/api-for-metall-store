import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Global exception handler for the API.
    Transforms all exceptions (including Django's ValidationError and raw 500 errors)
    into a unified format that supports content negotiation (JSON or HTML Browsable API).
    """
    # First, let REST framework handle its standard exceptions
    response = exception_handler(exc, context)

    # If it's a Django ValidationError, it wasn't caught by DRF. Catch it here!
    if isinstance(exc, DjangoValidationError):
        errors = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
        return Response({
            "success": False,
            "message": "Ma'lumotlarni tekshirishda xatolik yuz berdi.",
            "errors": errors
        }, status=status.HTTP_400_BAD_REQUEST)

    if response is not None:
        # Standardize the output format for all DRF exceptions
        custom_data = {
            "success": False,
            "message": "So'rovni bajarishda xatolik yuz berdi.",
            "errors": response.data
        }
        
        # Determine a better message if possible
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            custom_data["message"] = "Tizimga kirish talab etiladi."
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            custom_data["message"] = "Bu amalni bajarish uchun huquqingiz yo'q."
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            custom_data["message"] = "Ma'lumot topilmadi."
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            custom_data["message"] = "Juda ko'p so'rov yuborildi. Iltimos, birozdan so'ng qayta urinib ko'ring."
            
        response.data = custom_data
        return response

    # Securely handle raw Python exceptions (Internal Server Errors) to prevent Information Disclosure
    logger.exception("Kutilmagan server xatoligi yuz berdi: ", exc_info=exc)

    if settings.DEBUG:
        return None  # Let standard Django handle it (renders debug HTML page for developer)

    return Response({
        "success": False,
        "message": "Tizimda kutilmagan xatolik yuz berdi.",
        "errors": {"detail": "Ichki server xatoligi yuz berdi."}
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
