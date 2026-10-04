from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import Book, IssueBook, Student
from .templatetags.library_ui import library_overview


class LibraryInterfaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            title='A Room of One’s Own', author='Virginia Woolf',
            isbn_number='9780156787338', category='Essays', publisher='Harcourt',
            price='10.00', quantity=3, available_copies=2,
            published_date=date(1929, 10, 24),
        )
        cls.student = Student.objects.create(
            student_name='Test Reader', usn='TEST001', email='reader@example.com',
            phone_number='0000000000', department='Literature', semester=2,
        )
        IssueBook.objects.create(
            book=cls.book, student=cls.student, issue_date=date(2026, 10, 1),
            returned_status=False,
        )

    def test_dashboard_uses_actual_records_without_changing_them(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        overview = library_overview()
        self.assertEqual(
            {key: overview[key] for key in ('titles', 'copies', 'available', 'students', 'loans')},
            dict(titles=1, copies=3, available=2, students=1, loans=1),
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)
        self.assertEqual(IssueBook.objects.count(), 1)

    def test_all_read_only_pages_render_with_shared_theme(self):
        for name in ('home', 'books', 'students', 'about', 'contact'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="theme-toggle"')
                self.assertContains(response, '/static/css/style.css')
                self.assertNotContains(response, '<table')
        response = self.client.get(reverse('book_history', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Reader')
        self.assertContains(response, 'Return pending')

    def test_book_search_keeps_query_and_existing_action_urls(self):
        response = self.client.get(reverse('books'), {'q': 'Woolf'})
        self.assertContains(response, 'value="Woolf"')
        for name in ('issue_book', 'return_book', 'book_history'):
            self.assertContains(response, reverse(name, args=[self.book.pk]))
        self.assertContains(response, 'data-category="Essays"')
        self.assertContains(response, 'data-available="2"')
        response = self.client.get(reverse('books'), {'q': 'nonexistent'})
        self.assertContains(response, 'No books found')

    def test_empty_collection_and_dashboard_render(self):
        IssueBook.objects.all().delete()
        Book.objects.all().delete()
        Student.objects.all().delete()
        response = self.client.get(reverse('home'))
        self.assertEqual(library_overview()['available'], 0)
        self.assertContains(response, 'A new chapter is coming')
        self.assertContains(self.client.get(reverse('books')), 'The shelves are waiting')
        self.assertContains(self.client.get(reverse('students')), 'A community in the making')
