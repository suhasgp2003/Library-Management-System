from django.contrib import admin
from django.db import transaction
from .services import refresh_reservations
from .forms import BookForm, StudentForm
from .models import Book, IssueBook, ReminderLog, Reservation, Student

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookForm
    list_display = ['title', 'author', 'category', 'quantity', 'available_copies', 'is_archived']
    search_fields = ['title', 'author', 'isbn_number']
    list_filter = ['category', 'is_archived']
    readonly_fields = ['available_copies', 'is_archived']
    fields = BookForm.Meta.fields + ['available_copies', 'is_archived']

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        with transaction.atomic():
            if request.method == 'POST' and object_id:
                Book.objects.select_for_update().filter(pk=object_id).first()
            return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        refresh_reservations(obj)

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentForm
    list_display = ['student_name', 'usn', 'department', 'semester', 'is_archived']
    search_fields = ['student_name', 'usn', 'email']
    list_filter = ['department', 'is_archived']
    readonly_fields = ['is_archived']

    def has_delete_permission(self, request, obj=None):
        return False

class CirculationReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(IssueBook)
class IssueBookAdmin(CirculationReadOnlyAdmin):
    list_display = ['student', 'book', 'issue_date', 'due_date', 'return_date', 'returned_status']
    search_fields = ['student__student_name', 'book__title']
    list_filter = ['returned_status']

@admin.register(Reservation)
class ReservationAdmin(CirculationReadOnlyAdmin):
    list_display = ['student', 'book', 'status', 'created_at', 'expires_at']
    list_filter = ['status']

@admin.register(ReminderLog)
class ReminderLogAdmin(CirculationReadOnlyAdmin):
    list_display = ['kind', 'day', 'sent_at', 'loan', 'reservation']
