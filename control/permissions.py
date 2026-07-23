from rest_framework.permissions import BasePermission

class IsCashier(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'cashier'
        )

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff
