from rest_framework.permissions import BasePermission

class IsSysAdmin(BasePermission):
    """
    Allows access only to users with is_sysadmin = True in their JWT claims.
    Used for elevated actions within a tenant (above admin, below superuser).
    """
    message = "You do not have sysadmin privileges."

    def has_permission(self, request, view):
        if not request.auth:
            return False
        return bool(request.auth.get('is_sysadmin'))

class IsVerifiedAndApproved(BasePermission):
    """
    Blocks access to endpoints if the user has not been approved by an admin.
    """
    message = "Your account is pending approval by an administrator."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return bool(request.user.is_verified)


