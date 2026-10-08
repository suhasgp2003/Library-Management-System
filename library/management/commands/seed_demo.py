import os
from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from library.models import Book, IssueBook, Student
from library.services import reserve_for_reader

class Command(BaseCommand):
    help = 'Create synthetic local demo data. Requires DEBUG=true and DEMO_PASSWORD.'

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv('DEMO_PASSWORD')
        if not settings.DEBUG or not password or len(password) < 12:
            raise CommandError('Local demos require DEBUG=true and DEMO_PASSWORD of at least 12 characters.')
        User = get_user_model()
        librarian, created = User.objects.get_or_create(username='demo_librarian', defaults={'is_staff': True, 'email': 'librarian@example.com'})
        if created:
            librarian.set_password(password)
            librarian.save()
        students = []
        for index, name in enumerate(['demo_reader', 'demo_waiter']):
            user, created = User.objects.get_or_create(username=name, defaults={'email': f'{name}@example.com'})
            if created:
                user.set_password(password)
                user.save()
            student, _ = Student.objects.get_or_create(usn=f'DEMO00{index + 1}', defaults={'user': user, 'student_name': ['Asha Reader', 'Ravi Reader'][index], 'email': user.email, 'phone_number': '0000000000', 'department': 'Computer Science', 'semester': 4})
            students.append(student)
        entries = [('A Room of One’s Own', 'Virginia Woolf', '9780156787338', 'Essays'), ('Pride and Prejudice', 'Jane Austen', '9780141439518', 'Fiction'), ('The Great Gatsby', 'F. Scott Fitzgerald', '9780743273565', 'Fiction'), ('Clean Code', 'Robert C. Martin', '9780132350884', 'Technology')]
        for index, (title, author, isbn, category) in enumerate(entries):
            book, created = Book.objects.get_or_create(isbn_number=isbn, defaults={'title': title, 'author': author, 'category': category, 'publisher': 'Demo collection', 'price': '499.00', 'quantity': 1 if index == 0 else 3, 'available_copies': 0 if index == 0 else 3, 'published_date': date(2008, 1, 1)})
            if created and index == 0:
                IssueBook.objects.create(book=book, student=students[0], issue_date=timezone.localdate() - timedelta(days=20), due_date=timezone.localdate() - timedelta(days=6))
                reserve_for_reader(book.pk, students[1].pk)
        self.stdout.write(self.style.SUCCESS('Synthetic demo created. Logins: demo_librarian, demo_reader, demo_waiter. Password comes from DEMO_PASSWORD; existing passwords were not changed.'))
