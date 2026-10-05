"""Import library records into an empty MySQL database without modifying SQLite."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from library.models import Book, IssueBook, Student

class Command(BaseCommand):
    help = 'Import books, readers and loans from a legacy SQLite file into empty MySQL tables.'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.mysql':
            raise CommandError('The target must be MySQL.')
        if Book.objects.exists() or Student.objects.exists() or IssueBook.objects.exists():
            raise CommandError('Target library tables must be empty. Import never overwrites existing records.')
        path = Path(options['source']).resolve()
        try:
            source = sqlite3.connect('file:' + quote(path.as_posix(), safe='/:') + '?mode=ro', uri=True)
            source.row_factory = sqlite3.Row
            books = [dict(row) for row in source.execute('SELECT * FROM library_book')]
            students = [dict(row) for row in source.execute('SELECT * FROM library_student')]
            loans = [dict(row) for row in source.execute('SELECT * FROM library_issuebook')]
            source.close()
        except sqlite3.Error as error:
            raise CommandError(f'Cannot read the source library: {error}') from error
        active = {}
        for loan in loans:
            if not loan['returned_status']:
                active[loan['book_id']] = active.get(loan['book_id'], 0) + 1
        book_ids, student_ids = {}, {}
        for old in books:
            quantity = max(old['quantity'], active.get(old['id'], 0), 0)
            values = {name: old[name] for name in ['title', 'author', 'isbn_number', 'category', 'publisher', 'price', 'published_date']}
            book_ids[old['id']] = Book.objects.create(**values, quantity=quantity, available_copies=quantity - active.get(old['id'], 0)).pk
        for old in students:
            values = {name: old[name] for name in ['student_name', 'usn', 'email', 'phone_number', 'department', 'semester']}
            student_ids[old['id']] = Student.objects.create(**values).pk
        for old in loans:
            issued = date.fromisoformat(old['issue_date'])
            IssueBook.objects.create(book_id=book_ids[old['book_id']], student_id=student_ids[old['student_id']], issue_date=issued, due_date=issued + timedelta(days=14), return_date=old['return_date'] if old['returned_status'] else None, returned_status=bool(old['returned_status']))
        self.stdout.write(self.style.SUCCESS(f'Imported {len(books)} books, {len(students)} readers and {len(loans)} loans. Source unchanged; inventory reconciled.'))
