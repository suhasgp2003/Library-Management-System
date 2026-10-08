from datetime import timedelta
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db.models import Q
from django.utils import timezone
from .models import Book, IssueBook, Reservation, Student

class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input')

class BookForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn_number', 'category', 'publisher', 'price', 'quantity', 'published_date']
        widgets = {'published_date': forms.DateInput(attrs={'type': 'date'})}

    def clean_isbn_number(self):
        return self.cleaned_data['isbn_number'].replace('-', '').replace(' ', '').upper()

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.instance.pk:
            minimum = IssueBook.objects.filter(book=self.instance, returned_status=False).count() + Reservation.objects.filter(book=self.instance, status='ready', active_slot=1).count()
            if quantity < minimum:
                raise forms.ValidationError('Total copies cannot be fewer than active loans and ready reservation holds.')
        return quantity

    def _post_clean(self):
        if 'quantity' in self.cleaned_data:
            active = IssueBook.objects.filter(book=self.instance, returned_status=False).count() if self.instance.pk else 0
            self.instance.available_copies = max(self.cleaned_data['quantity'] - active, 0)
        super()._post_clean()

class StudentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_name', 'usn', 'email', 'phone_number', 'department', 'semester', 'user']
        help_texts = {'user': 'Link an unlinked student login created by an administrator. Existing readers should not re-register.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        query = Q(reader_profile__isnull=True)
        if self.instance.user_id:
            query |= Q(pk=self.instance.user_id)
        self.fields['user'].queryset = get_user_model().objects.filter(query, is_staff=False, is_active=True)

class RegistrationForm(StyledFormMixin, UserCreationForm):
    student_name = forms.CharField(max_length=100, label='Full name')
    usn = forms.CharField(max_length=20, label='USN')
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=10, validators=[RegexValidator(r'^\d{10}$', 'Enter a 10-digit phone number.')])
    department = forms.CharField(max_length=100)
    semester = forms.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])

    class Meta(UserCreationForm.Meta):
        fields = ['username', 'student_name', 'usn', 'email', 'phone_number', 'department', 'semester']

    def clean_usn(self):
        usn = self.cleaned_data['usn'].strip().upper()
        if Student.objects.filter(usn=usn).exists():
            raise forms.ValidationError('This USN is already registered. Ask the librarian to link your existing reader record.')
        return usn

class IssueForm(StyledFormMixin, forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.none(), label='Reader')
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.filter(is_archived=False).filter(Q(user__isnull=True) | Q(user__is_active=True))
        self.fields['due_date'].initial = timezone.localdate() + timedelta(days=settings.LOAN_DAYS)

    def clean_due_date(self):
        due = self.cleaned_data['due_date']
        if due < timezone.localdate():
            raise forms.ValidationError('The due date cannot be in the past.')
        return due

class ReturnForm(StyledFormMixin, forms.Form):
    loan = forms.ModelChoiceField(queryset=IssueBook.objects.none(), label='Active loan to return')

    def __init__(self, *args, book, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['loan'].queryset = IssueBook.objects.filter(book=book, returned_status=False).select_related('student', 'book')
