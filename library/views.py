from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from . import services
from .access import librarian_required, reader_for
from .forms import BookForm, IssueForm, RegistrationForm, ReturnForm, StudentForm
from .models import Book, IssueBook, Reservation, Student

def paginate(request, queryset, size=12):
    page = Paginator(queryset, size).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return page, query.urlencode()

@login_required
def home(request):
    if request.user.is_staff:
        return render(request, 'home.html')
    student = reader_for(request.user)
    loans = IssueBook.objects.filter(student=student).select_related('book') if student else IssueBook.objects.none()
    reservations = Reservation.objects.filter(student=student).select_related('book') if student else Reservation.objects.none()
    return render(request, 'dashboard_student.html', {'reader': student, 'loans': loans[:10], 'active_count': loans.filter(returned_status=False).count(), 'overdue_count': loans.filter(returned_status=False, due_date__lt=timezone.localdate()).count(), 'reservations': reservations[:10]})

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def books(request):
    queryset = Book.objects.with_availability()
    if not (request.user.is_authenticated and request.user.is_staff and request.GET.get('archived') == '1'):
        queryset = queryset.filter(is_archived=False)
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(category__icontains=query) | Q(isbn_number__icontains=query))
    if request.GET.get('category'):
        queryset = queryset.filter(category=request.GET['category'])
    availability = request.GET.get('availability')
    if availability == 'available':
        queryset = queryset.filter(free_copies__gt=0)
    elif availability == 'unavailable':
        queryset = queryset.filter(free_copies=0)
    ordering = {'title': 'title', 'author': 'author', 'copies': '-free_copies'}.get(request.GET.get('sort'), 'title')
    page, page_query = paginate(request, queryset.order_by(ordering, 'pk'))
    return render(request, 'books.html', {'books': page, 'page_obj': page, 'page_query': page_query, 'categories': Book.objects.filter(is_archived=False).order_by('category').values_list('category', flat=True).distinct()})

@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                Student.objects.create(user=user, **{name: form.cleaned_data[name] for name in ['student_name', 'usn', 'email', 'phone_number', 'department', 'semester']})
        except IntegrityError:
            form.add_error(None, 'The username or USN was just registered. Please use another or contact the librarian.')
        else:
            login(request, user)
            messages.success(request, 'Welcome! Your reader account is ready.')
            return redirect('home')
    return render(request, 'manage_form.html', {'form': form, 'heading': 'Join the reading room', 'description': 'Create your student login. Existing readers should ask a librarian to link their record.', 'submit_label': 'Create student account'})

@librarian_required
@require_http_methods(['GET', 'POST'])
def issue_book(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    form = IssueForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            services.issue_to_reader(book.pk, form.cleaned_data['student'].pk, form.cleaned_data['due_date'])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Book issued to the selected reader.')
            return redirect('loans')
    return render(request, 'manage_form.html', {'form': form, 'heading': f'Issue {book.title}', 'description': 'Select the reader and due date. Inventory updates only when this form is submitted.', 'submit_label': 'Confirm issue'})

@librarian_required
@require_http_methods(['GET', 'POST'])
def return_book(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    form = ReturnForm(request.POST or None, book=book)
    if request.method == 'POST' and form.is_valid():
        try:
            services.return_loan(form.cleaned_data['loan'].pk)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Loan returned and inventory updated.')
            return redirect('loans')
    return render(request, 'manage_form.html', {'form': form, 'heading': f'Return {book.title}', 'description': 'Choose the exact active loan. Returning twice will not increase stock.', 'submit_label': 'Confirm return'})

@librarian_required
@require_POST
def loan_return(request, loan_id):
    get_object_or_404(IssueBook, pk=loan_id)
    try:
        services.return_loan(loan_id)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
    else:
        messages.success(request, 'Book returned successfully.')
    return redirect('loans')

@login_required
def loans(request):
    queryset = IssueBook.objects.select_related('book', 'student')
    if not request.user.is_staff:
        student = reader_for(request.user)
        queryset = queryset.filter(student=student) if student else queryset.none()
    state = request.GET.get('status', 'active')
    if state == 'overdue':
        queryset = queryset.filter(returned_status=False, due_date__lt=timezone.localdate())
    elif state == 'returned':
        queryset = queryset.filter(returned_status=True)
    elif state == 'active':
        queryset = queryset.filter(returned_status=False)
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(Q(book__title__icontains=query) | Q(student__student_name__icontains=query) | Q(student__usn__icontains=query))
    page, page_query = paginate(request, queryset)
    return render(request, 'loans.html', {'loans': page, 'page_obj': page, 'page_query': page_query, 'status': state})

@librarian_required
def students(request):
    queryset = Student.objects.select_related('user')
    if request.GET.get('archived') != '1':
        queryset = queryset.filter(is_archived=False)
    if request.GET.get('q'):
        query = request.GET['q']
        queryset = queryset.filter(Q(student_name__icontains=query) | Q(usn__icontains=query) | Q(email__icontains=query) | Q(department__icontains=query))
    if request.GET.get('department'):
        queryset = queryset.filter(department=request.GET['department'])
    page, page_query = paginate(request, queryset)
    return render(request, 'students.html', {'students': page, 'page_obj': page, 'page_query': page_query, 'departments': Student.objects.filter(is_archived=False).order_by('department').values_list('department', flat=True).distinct()})

def book_history(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    if book.is_archived and not (request.user.is_authenticated and request.user.is_staff):
        raise PermissionDenied('This book has been archived.')
    history = IssueBook.objects.filter(book=book).select_related('student')
    if not (request.user.is_authenticated and request.user.is_staff):
        student = reader_for(request.user)
        history = history.filter(student=student) if student else history.none()
    page, page_query = paginate(request, history)
    return render(request, 'book-history.html', {'book': book, 'history': page, 'page_obj': page, 'page_query': page_query})

@librarian_required
@require_http_methods(['GET', 'POST'])
def book_edit(request, book_id=None):
    with transaction.atomic():
        book = get_object_or_404(Book.objects.select_for_update(), pk=book_id) if book_id else Book()
        form = BookForm(request.POST or None, instance=book)
        if request.method == 'POST' and form.is_valid():
            if book.pk and form.cleaned_data['quantity'] < Reservation.objects.filter(book=book, status='ready').count() + IssueBook.objects.filter(book=book, returned_status=False).count():
                form.add_error('quantity', 'Copies are held for ready reservations. Cancel those holds before reducing stock.')
            else:
                form.save()
                services.refresh_reservations(book)
                messages.success(request, 'Book saved. Available copies were calculated from active loans.')
                return redirect('books')
    return render(request, 'manage_form.html', {'form': form, 'heading': 'Edit book' if book_id else 'Add a book', 'submit_label': 'Save book'})

@librarian_required
@require_http_methods(['GET', 'POST'])
def student_edit(request, student_id=None):
    with transaction.atomic():
        student = get_object_or_404(Student.objects.select_for_update(), pk=student_id) if student_id else Student()
        form = StudentForm(request.POST or None, instance=student)
        if request.method == 'POST' and form.is_valid():
            form.save()
            messages.success(request, 'Reader saved.')
            return redirect('students')
    return render(request, 'manage_form.html', {'form': form, 'heading': 'Edit reader' if student_id else 'Add a reader', 'submit_label': 'Save reader'})

@librarian_required
@require_POST
def book_archive(request, book_id):
    get_object_or_404(Book, pk=book_id)
    try:
        services.archive_book(book_id)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
    else:
        messages.success(request, 'Book archived. Borrowing history is preserved.')
    return redirect('books')

@librarian_required
@require_POST
def student_archive(request, student_id):
    get_object_or_404(Student, pk=student_id)
    try:
        services.archive_student(student_id)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
    else:
        messages.success(request, 'Reader archived. Borrowing history is preserved.')
    return redirect('students')

@librarian_required
@require_POST
def book_restore(request, book_id):
    Book.objects.filter(pk=get_object_or_404(Book, pk=book_id).pk).update(is_archived=False)
    messages.success(request, 'Book restored.')
    return redirect('books')

@librarian_required
@require_POST
def student_restore(request, student_id):
    Student.objects.filter(pk=get_object_or_404(Student, pk=student_id).pk).update(is_archived=False)
    messages.success(request, 'Reader restored.')
    return redirect('students')

@login_required
@require_POST
def reserve_book(request, book_id):
    get_object_or_404(Book, pk=book_id)
    student = reader_for(request.user)
    if not student:
        raise PermissionDenied('An active student profile is required to reserve a book.')
    try:
        services.reserve_for_reader(book_id, student.pk)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
    else:
        messages.success(request, 'You joined the reservation queue.')
    return redirect('reservations')

@login_required
def reservations(request):
    queryset = Reservation.objects.select_related('book', 'student')
    if not request.user.is_staff:
        student = reader_for(request.user)
        queryset = queryset.filter(student=student) if student else queryset.none()
    if request.GET.get('closed') != '1':
        queryset = queryset.filter(active_slot=1)
    page, page_query = paginate(request, queryset)
    return render(request, 'reservations.html', {'reservations': page, 'page_obj': page, 'page_query': page_query})

@login_required
@require_POST
def reservation_cancel(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    student = reader_for(request.user)
    if not request.user.is_staff and (not student or reservation.student_id != student.pk):
        raise PermissionDenied('This reservation does not belong to you.')
    try:
        services.cancel_reservation(reservation_id, None if request.user.is_staff else student.pk)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
    else:
        messages.success(request, 'Reservation cancelled.')
    return redirect('reservations')
