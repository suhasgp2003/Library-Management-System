from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Student

def librarian_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied('This action is available to librarians only.')
        return view(request, *args, **kwargs)
    return wrapped

def reader_for(user):
    return Student.objects.filter(user=user, is_archived=False).first() if user.is_authenticated else None
