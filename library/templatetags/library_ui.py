"""Read-only dashboard analytics; circulation lives in transactional services."""
from django import template
from django.db.models import Sum
from library.models import Book, IssueBook, Student

register = template.Library()


@register.simple_tag
def library_page_label(route, is_librarian=False):
    """Human-readable location for the shared header; no database access."""
    labels = {
        'home': 'Overview' if is_librarian else 'My reading room',
        'books': 'Book collection', 'book_history': 'Book details',
        'book_add': 'Add a book', 'book_edit': 'Edit book',
        'students': 'Readers', 'student_add': 'Add a reader',
        'student_edit': 'Edit reader',
        'loans': 'Borrowing desk' if is_librarian else 'My loans',
        'reservations': 'Reservations', 'issue_book': 'Issue a book',
        'return_book': 'Return a book', 'about': 'About the library',
        'contact': 'Get in touch', 'login': 'Sign in', 'register': 'Join the library',
        'password_change': 'Account settings', 'password_change_done': 'Account settings',
    }
    return labels.get(route, 'Your library')


@register.simple_tag
def library_overview():
    totals = Book.objects.filter(is_archived=False).aggregate(copies=Sum('quantity'), available=Sum('available_copies'))
    copies = totals['copies'] or 0
    available = totals['available'] or 0
    return {
        'titles': Book.objects.filter(is_archived=False).count(),
        'copies': copies,
        'available': available,
        'students': Student.objects.filter(is_archived=False).count(),
        'loans': IssueBook.objects.filter(returned_status=False).count(),
        'books': Book.objects.with_availability().filter(is_archived=False).order_by('-id')[:4],
        'activity': IssueBook.objects.select_related('book', 'student').order_by('-id')[:4],
    }
