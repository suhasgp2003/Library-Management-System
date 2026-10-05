from .access import reader_for

def library_access(request):
    return {'is_librarian': request.user.is_authenticated and request.user.is_staff, 'current_reader': reader_for(request.user)}
