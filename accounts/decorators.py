from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Allow a view only for logged-in, active users with one of the given roles."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("You do not have access to this page.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


candidate_required = role_required("candidate")
employer_required = role_required("employer")
admin_required = role_required("admin")
