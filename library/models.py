from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.db.models.functions import Cast, Coalesce, Greatest
from .validators import validate_isbn

class BookQuerySet(models.QuerySet):
    def with_availability(self):
        held = Reservation.objects.filter(book_id=models.OuterRef('pk'), status='ready', active_slot=1, expires_at__gt=timezone.now()).order_by().values('book_id').annotate(total=models.Count('pk')).values('total')
        return self.annotate(held_copies=Coalesce(models.Subquery(held, output_field=models.IntegerField()), models.Value(0))).annotate(free_copies=Greatest(Cast('available_copies', models.IntegerField()) - models.F('held_copies'), models.Value(0)))

class Book(models.Model):
    objects = BookQuerySet.as_manager()
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    isbn_number = models.CharField(max_length=25, validators=[validate_isbn])
    category = models.CharField(max_length=50, db_index=True)
    publisher = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=0)
    available_copies = models.PositiveIntegerField(default=0)
    published_date = models.DateField()
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['title', 'pk']
        constraints = [models.CheckConstraint(condition=models.Q(available_copies__lte=models.F('quantity')), name='book_stock_within_quantity'), models.CheckConstraint(condition=models.Q(price__gte=0), name='book_price_nonnegative')]

    def __str__(self):
        return self.title

class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='reader_profile')
    student_name = models.CharField(max_length=100)
    usn = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=10, validators=[RegexValidator(r'^\d{10}$', 'Enter a 10-digit phone number.')])
    department = models.CharField(max_length=100, db_index=True)
    semester = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    is_archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['student_name', 'pk']

    def __str__(self):
        return self.student_name

class IssueBook(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='loans')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='loans')
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    returned_status = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-issue_date', '-pk']
        indexes = [models.Index(fields=['returned_status', 'due_date'], name='loan_status_due_idx')]
        constraints = [
            models.CheckConstraint(condition=models.Q(due_date__gte=models.F('issue_date')), name='loan_due_after_issue'),
            models.CheckConstraint(condition=models.Q(return_date__isnull=True) | models.Q(return_date__gte=models.F('issue_date')), name='loan_return_after_issue'),
            models.CheckConstraint(condition=models.Q(returned_status=True) | models.Q(return_date__isnull=True), name='active_loan_has_no_return_date'),
        ]

    @property
    def is_overdue(self):
        return not self.returned_status and self.due_date < timezone.localdate()

    def __str__(self):
        return f'{self.student.student_name} — {self.book.title}'

class Reservation(models.Model):
    class Status(models.TextChoices):
        WAITING = 'waiting', 'Waiting'
        READY = 'ready', 'Ready to collect'
        FULFILLED = 'fulfilled', 'Fulfilled'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='reservations')
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='reservations')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.WAITING)
    created_at = models.DateTimeField(default=timezone.now)
    ready_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    # NULL permits historical rows; 1 makes each active book-reader reservation unique on MySQL.
    active_slot = models.PositiveSmallIntegerField(default=1, null=True, editable=False)

    class Meta:
        ordering = ['created_at', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['book', 'student', 'active_slot'], name='unique_active_reservation'),
            models.CheckConstraint(condition=(models.Q(status__in=['waiting', 'ready'], active_slot=1) | models.Q(status__in=['fulfilled', 'cancelled', 'expired'], active_slot__isnull=True)), name='reservation_status_slot_matches'),
        ]

class ReminderLog(models.Model):
    loan = models.ForeignKey(IssueBook, on_delete=models.PROTECT, null=True, blank=True)
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=16)
    day = models.DateField(default=timezone.localdate)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['loan', 'kind', 'day'], name='one_loan_reminder_per_day'),
            models.UniqueConstraint(fields=['reservation', 'kind', 'day'], name='one_reservation_reminder_per_day'),
            models.CheckConstraint(condition=(models.Q(loan__isnull=False, reservation__isnull=True) | models.Q(loan__isnull=True, reservation__isnull=False)), name='reminder_has_one_subject'),
        ]
