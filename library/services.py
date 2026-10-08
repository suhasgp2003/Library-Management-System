"""Circulation operations lock book first, then reader/loan, in one transaction."""
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Book, IssueBook, Reservation, Student

def refresh_reservations(book):
    """Caller must hold the book lock. Allocate available copies in queue order."""
    now = timezone.now()
    queue = list(Reservation.objects.select_for_update().filter(book=book, active_slot=1).order_by('created_at', 'pk'))
    active = []
    for reservation in queue:
        inactive = reservation.student.is_archived or (reservation.student.user_id and not reservation.student.user.is_active)
        if inactive or (reservation.status == Reservation.Status.READY and reservation.expires_at <= now):
            reservation.status = Reservation.Status.CANCELLED if inactive else Reservation.Status.EXPIRED
            reservation.active_slot = None
            reservation.save(update_fields=['status', 'active_slot'])
        else:
            active.append(reservation)
    ready_count = sum(item.status == Reservation.Status.READY for item in active)
    free = max(book.available_copies - ready_count, 0)
    for reservation in active:
        if free and reservation.status == Reservation.Status.WAITING:
            reservation.status = Reservation.Status.READY
            reservation.ready_at = now
            reservation.expires_at = now + timedelta(days=settings.RESERVATION_HOLD_DAYS)
            reservation.save(update_fields=['status', 'ready_at', 'expires_at'])
            free -= 1
    return active

@transaction.atomic
def issue_to_reader(book_id, student_id, due_date):
    book = Book.objects.select_for_update().get(pk=book_id)
    student = Student.objects.select_for_update().get(pk=student_id)
    today = timezone.localdate()
    if book.is_archived or student.is_archived or (student.user_id and not student.user.is_active):
        raise ValidationError('This book or reader is inactive.')
    if due_date < today:
        raise ValidationError('The due date cannot be in the past.')
    if book.available_copies <= 0:
        raise ValidationError('No copies are available for this book.')
    loans = IssueBook.objects.filter(student=student, returned_status=False)
    if loans.filter(book=book).exists():
        raise ValidationError('This reader already has an active loan for this book.')
    if loans.count() >= settings.MAX_ACTIVE_LOANS:
        raise ValidationError(f'A reader can have at most {settings.MAX_ACTIVE_LOANS} active loans.')
    queue = refresh_reservations(book)
    ready = [item for item in queue if item.status == Reservation.Status.READY]
    own = next((item for item in ready if item.student_id == student.pk), None)
    if not own and book.available_copies <= len(ready):
        raise ValidationError('Available copies are held for readers in the reservation queue.')
    loan = IssueBook.objects.create(book=book, student=student, issue_date=today, due_date=due_date)
    book.available_copies -= 1
    book.save(update_fields=['available_copies'])
    if own:
        own.status = Reservation.Status.FULFILLED
        own.active_slot = None
        own.save(update_fields=['status', 'active_slot'])
    return loan

@transaction.atomic
def return_loan(loan_id):
    book_id = IssueBook.objects.values_list('book_id', flat=True).get(pk=loan_id)
    book = Book.objects.select_for_update().get(pk=book_id)
    loan = IssueBook.objects.select_for_update().get(pk=loan_id)
    if loan.returned_status:
        raise ValidationError('This loan has already been returned.')
    if book.available_copies >= book.quantity:
        raise ValidationError('Inventory is inconsistent. Ask a librarian to review the stock.')
    loan.returned_status = True
    loan.return_date = timezone.localdate()
    loan.save(update_fields=['returned_status', 'return_date'])
    book.available_copies += 1
    book.save(update_fields=['available_copies'])
    refresh_reservations(book)
    return loan

@transaction.atomic
def reserve_for_reader(book_id, student_id):
    book = Book.objects.select_for_update().get(pk=book_id)
    student = Student.objects.select_for_update().get(pk=student_id)
    if book.is_archived or student.is_archived or (student.user_id and not student.user.is_active):
        raise ValidationError('This book or reader is inactive.')
    if IssueBook.objects.filter(book=book, student=student, returned_status=False).exists():
        raise ValidationError('You already have an active loan for this book.')
    queue = refresh_reservations(book)
    if any(item.student_id == student.pk for item in queue):
        raise ValidationError('You already have an active reservation for this book.')
    if book.available_copies > sum(item.status == Reservation.Status.READY for item in queue):
        raise ValidationError('A copy is available. Ask a librarian to issue it to you.')
    return Reservation.objects.create(book=book, student=student)

@transaction.atomic
def cancel_reservation(reservation_id, student_id=None):
    book_id = Reservation.objects.values_list('book_id', flat=True).get(pk=reservation_id)
    book = Book.objects.select_for_update().get(pk=book_id)
    reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
    if student_id is not None and reservation.student_id != student_id:
        raise ValidationError('This reservation does not belong to you.')
    if reservation.active_slot is None:
        raise ValidationError('This reservation is already closed.')
    reservation.status = Reservation.Status.CANCELLED
    reservation.active_slot = None
    reservation.save(update_fields=['status', 'active_slot'])
    refresh_reservations(book)
    return reservation

@transaction.atomic
def archive_book(book_id):
    book = Book.objects.select_for_update().get(pk=book_id)
    if IssueBook.objects.filter(book=book, returned_status=False).exists():
        raise ValidationError('Return all active loans before archiving this book.')
    if Reservation.objects.filter(book=book, active_slot=1).exists():
        raise ValidationError('Close active reservations before archiving this book.')
    book.is_archived = True
    book.save(update_fields=['is_archived'])

@transaction.atomic
def archive_student(student_id):
    student = Student.objects.select_for_update().get(pk=student_id)
    if IssueBook.objects.filter(student=student, returned_status=False).exists() or Reservation.objects.filter(student=student, active_slot=1).exists():
        raise ValidationError('Close this reader’s loans and reservations before archiving.')
    student.is_archived = True
    student.save(update_fields=['is_archived'])
