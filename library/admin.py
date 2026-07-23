from django.contrib import admin

# Register your models here.
from .models import Book,Student,IssueBook

admin.site.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display=["title","author","category","available_copies"]
    search_fields=["title","author"]
    list_filter=["title"]
    ordering=["title"]
admin.site.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display=["student_name","usn","department","semester"]
    search_fields=["student_name","usn","department"]
    list_filter=["department","semester"]
    ordering=["student_name"]

admin.site.register(IssueBook)
class IssueBookAdmin(admin.ModelAdmin):
    list_display=["student","book","issue_date","returned_date","returned_status"]
    search_fields=["student__student_name","book__title"]
    list_filter=["returned_status"]
