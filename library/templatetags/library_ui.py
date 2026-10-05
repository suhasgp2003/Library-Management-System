"""Read-only dashboard analytics; circulation lives in transactional services."""
from django import template
from django.db.models import Sum
from library.models import Book, IssueBook, Student

register = template.Library()


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
