from functools import wraps
from django.http import JsonResponse


def _get_profile(user):
    """Safely retrieve the UserProfile, returns None if missing."""
    return getattr(user, 'profile', None)


def role_required(*allowed_roles):
    """
    Restrict a view to users whose profile.role is in allowed_roles.
    Also accepts superusers unconditionally.

    Usage:
        @role_required('staff')
        @role_required('manager', 'staff')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = _get_profile(request.user)
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            return JsonResponse(
                {'status': 'error', 'message': 'Akses ditolak. Anda tidak punya izin untuk aksi ini.'},
                status=403,
            )
        return wrapper
    return decorator


def staff_required(view_func):
    """Shortcut: only Staff (and superusers) can access."""
    return role_required('staff')(view_func)


def manager_required(view_func):
    """Shortcut: only Managers (and superusers) can access."""
    return role_required('manager')(view_func)


def manager_or_staff_required(view_func):
    """Shortcut: both Manager and Staff can access."""
    return role_required('manager', 'staff')(view_func)