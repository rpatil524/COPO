# Created by fshaw at 11/06/2018
from django.core.exceptions import PermissionDenied

def user_is_superuser(function):
    def wrap(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        else:
            return function(request, *args, **kwargs)
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap