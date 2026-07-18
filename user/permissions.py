from rest_framework import permissions

class IsAdminOrOmborchi(permissions.BasePermission):
    """
    Allows access to Admin, Omborchi roles, or superusers.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            return request.user.xodim.rol in ['admin', 'omborchi']
        except AttributeError:
            return False


class IsAdminOrOmborchiOrReadOnly(permissions.BasePermission):
    """
    Allows write access to Admin/Omborchi roles/superusers, and read-only access to other employees.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
            
        if request.method in permissions.SAFE_METHODS:
            return hasattr(request.user, 'xodim')
            
        try:
            return request.user.xodim.rol in ['admin', 'omborchi']
        except AttributeError:
            return False


class IsEmployee(permissions.BasePermission):
    """
    Allows access to authenticated employees or superusers.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or hasattr(request.user, 'xodim')
