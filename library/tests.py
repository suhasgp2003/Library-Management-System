from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from io import StringIO
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from . import services
from .forms import BookForm
from .models import Book, IssueBook, ReminderLog, Reservation, Student


def make_book(**overrides):
    values = dict(title='A Room of One’s Own', author='Virginia Woolf', isbn_number='9780156787338', category='Essays', publisher='Harcourt', price='100.00', quantity=3, available_copies=3, published_date=date(1929, 10, 24))
    values.update(overrides)
    return Book.objects.create(**values)

def make_student(index, user=None):
    return Student.objects.create(user=user, student_name=f'Reader {index}', usn=f'TEST{index}', email=f'reader{index}@example.com', phone_number='0000000000', department='Literature', semester=2)

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LibraryWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user('librarian', password='TestPassword!2026', is_staff=True)
        cls.user1 = User.objects.create_user('reader1', password='TestPassword!2026')
        cls.user2 = User.objects.create_user('reader2', password='TestPassword!2026')
        cls.reader1 = make_student(1, cls.user1)
        cls.reader2 = make_student(2, cls.user2)
        cls.book = make_book()
        cls.loan = services.issue_to_reader(cls.book.pk, cls.reader1.pk, timezone.localdate() + timedelta(days=14))

    def as_staff(self):
        self.client.force_login(self.staff)

    def test_public_catalogue_hides_private_actions_and_borrowers(self):
        response = self.client.get(reverse('books'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('issue_book', args=[self.book.pk]))
        response = self.client.get(reverse('book_history', args=[self.book.pk]))
        self.assertNotContains(response, self.reader1.usn)
        self.assertNotContains(response, self.reader1.student_name)

    def test_anonymous_dashboard_and_directory_require_login(self):
        for name in ['home', 'students', 'loans', 'reservations']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_student_cannot_manage_books_readers_or_loans(self):
        self.client.force_login(self.user1)
        for name in ['book_add', 'student_add', 'students']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        for name in ['issue_book', 'return_book', 'book_edit', 'book_archive']:
            response = self.client.post(reverse(name, args=[self.book.pk]), {'student': self.reader2.pk})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post(reverse('loan_return', args=[self.loan.pk])).status_code, 403)

    def test_student_only_sees_their_history_and_dashboard(self):
        self.client.force_login(self.user2)
        for url in [reverse('home'), reverse('loans') + '?status=all', reverse('book_history', args=[self.book.pk])]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.reader1.usn)
            self.assertNotContains(response, 'Return this loan')
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('loans')), self.book.title)

    def test_get_requests_never_issue_or_return(self):
        self.as_staff()
        self.assertEqual(self.client.get(reverse('issue_book', args=[self.book.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('return_book', args=[self.book.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('loan_return', args=[self.loan.pk])).status_code, 405)
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)
        self.assertEqual(IssueBook.objects.count(), 1)

    def test_csrf_is_required_for_circulation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.post(reverse('loan_return', args=[self.loan.pk])).status_code, 403)
        self.assertEqual(client.post(reverse('issue_book', args=[self.book.pk]), {'student': self.reader2.pk, 'due_date': timezone.localdate()}).status_code, 403)

    def test_issue_uses_selected_student_and_due_date(self):
        self.as_staff()
        due = timezone.localdate() + timedelta(days=7)
        response = self.client.post(reverse('issue_book', args=[self.book.pk]), {'student': self.reader2.pk, 'due_date': due.isoformat()})
        self.assertRedirects(response, reverse('loans'))
        loan = IssueBook.objects.get(student=self.reader2)
        self.assertEqual(loan.due_date, due)
        self.assertIsNone(loan.return_date)
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)

    def test_duplicate_borrow_is_rejected_without_stock_change(self):
        with self.assertRaises(ValidationError):
            services.issue_to_reader(self.book.pk, self.reader1.pk, timezone.localdate())
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)

    def test_unavailable_book_and_past_due_date_are_rejected(self):
        unavailable = make_book(title='Unavailable', quantity=0, available_copies=0)
        with self.assertRaises(ValidationError):
            services.issue_to_reader(unavailable.pk, self.reader2.pk, timezone.localdate())
        with self.assertRaises(ValidationError):
            services.issue_to_reader(self.book.pk, self.reader2.pk, timezone.localdate() - timedelta(days=1))

    @override_settings(MAX_ACTIVE_LOANS=1)
    def test_reader_loan_limit_is_enforced(self):
        other = make_book(title='Another title')
        with self.assertRaises(ValidationError):
            services.issue_to_reader(other.pk, self.reader1.pk, timezone.localdate())

    def test_return_twice_only_updates_stock_once(self):
        services.return_loan(self.loan.pk)
        with self.assertRaises(ValidationError):
            services.return_loan(self.loan.pk)
        self.book.refresh_from_db()
        self.loan.refresh_from_db()
        self.assertEqual(self.book.available_copies, 3)
        self.assertTrue(self.loan.returned_status)
        self.assertEqual(self.loan.return_date, timezone.localdate())

    def test_return_form_rejects_a_loan_from_a_different_book(self):
        other = make_book(title='Other')
        self.as_staff()
        response = self.client.post(reverse('return_book', args=[other.pk]), {'loan': self.loan.pk})
        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        self.assertFalse(self.loan.returned_status)

    def test_transaction_rolls_back_inventory_if_loan_creation_fails(self):
        with patch('library.services.IssueBook.objects.create', side_effect=RuntimeError('simulated write failure')):
            with self.assertRaises(RuntimeError):
                services.issue_to_reader(self.book.pk, self.reader2.pk, timezone.localdate())
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)

    def test_inventory_constraints_are_enforced_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Book.objects.filter(pk=self.book.pk).update(available_copies=4)

    def test_book_form_validates_isbn_and_stock(self):
        values = {'title': 'Edited title', 'author': 'Author', 'isbn_number': 'invalid', 'category': 'Essays', 'publisher': 'Publisher', 'price': '10.00', 'quantity': 0, 'published_date': '2020-01-01'}
        form = BookForm(values, instance=self.book)
        self.assertFalse(form.is_valid())
        self.assertIn('isbn_number', form.errors)
        self.assertIn('quantity', form.errors)
        values.update(isbn_number='978-0-156-78733-8', quantity=4)
        form = BookForm(values, instance=Book.objects.get(pk=self.book.pk))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.available_copies, 3)

    def test_edit_book_recalculates_inventory(self):
        self.as_staff()
        response = self.client.post(reverse('book_edit', args=[self.book.pk]), {'title': self.book.title, 'author': self.book.author, 'isbn_number': self.book.isbn_number, 'category': self.book.category, 'publisher': self.book.publisher, 'price': self.book.price, 'quantity': 5, 'published_date': self.book.published_date})
        self.assertRedirects(response, reverse('books'))
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 4)

    def test_archive_preserves_history_and_rejects_active_loans(self):
        with self.assertRaises(ValidationError):
            services.archive_book(self.book.pk)
        with self.assertRaises(ValidationError):
            services.archive_student(self.reader1.pk)
        services.return_loan(self.loan.pk)
        services.archive_book(self.book.pk)
        services.archive_student(self.reader1.pk)
        self.assertEqual(IssueBook.objects.count(), 1)
        with self.assertRaises(ProtectedError):
            self.book.delete()
        self.assertNotContains(self.client.get(reverse('books')), self.book.title)

    def test_search_filters_and_pagination_work_on_entire_collection(self):
        for index in range(14):
            make_book(title=f'Title {index:02d}', category='Fiction')
        response = self.client.get(reverse('books'), {'category': 'Fiction', 'page': 2, 'sort': 'title'})
        self.assertEqual(response.context['page_obj'].paginator.count, 14)
        self.assertEqual(len(response.context['books']), 2)
        response = self.client.get(reverse('books'), {'q': 'Woolf', 'category': 'Essays', 'availability': 'available'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(response, 'value="Woolf"')

    def test_registration_creates_only_student_account(self):
        response = self.client.post(reverse('register'), {'username': 'newreader', 'student_name': 'New Reader', 'usn': 'NEW001', 'email': 'new@example.com', 'phone_number': '1234567890', 'department': 'Science', 'semester': 2, 'password1': 'StrongReader!2026', 'password2': 'StrongReader!2026', 'is_staff': 'true'})
        self.assertRedirects(response, reverse('home'))
        user = get_user_model().objects.get(username='newreader')
        self.assertFalse(user.is_staff)
        self.assertEqual(user.reader_profile.usn, 'NEW001')

    def test_existing_profile_cannot_be_claimed_through_registration(self):
        response = self.client.post(reverse('register'), {'username': 'intruder', 'student_name': 'Fake', 'usn': self.reader1.usn, 'email': self.reader1.email, 'phone_number': '1234567890', 'department': 'Science', 'semester': 2, 'password1': 'StrongReader!2026', 'password2': 'StrongReader!2026'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='intruder').exists())

    def unavailable_book(self):
        book = make_book(title='Reserved book', quantity=1, available_copies=1)
        loan = services.issue_to_reader(book.pk, self.reader1.pk, timezone.localdate() + timedelta(days=14))
        return book, loan

    def test_reservation_is_unique_and_return_makes_it_ready(self):
        book, loan = self.unavailable_book()
        reservation = services.reserve_for_reader(book.pk, self.reader2.pk)
        with self.assertRaises(ValidationError):
            services.reserve_for_reader(book.pk, self.reader2.pk)
        services.return_loan(loan.pk)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.READY)
        self.assertIsNotNone(reservation.expires_at)
        with self.assertRaises(ValidationError):
            services.issue_to_reader(book.pk, self.reader1.pk, timezone.localdate())
        services.issue_to_reader(book.pk, self.reader2.pk, timezone.localdate())
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.FULFILLED)
        self.assertIsNone(reservation.active_slot)

    def test_cancel_releases_hold_and_expired_hold_advances_queue(self):
        book, loan = self.unavailable_book()
        first = services.reserve_for_reader(book.pk, self.reader2.pk)
        reader3 = make_student(3)
        second = services.reserve_for_reader(book.pk, reader3.pk)
        services.return_loan(loan.pk)
        Reservation.objects.filter(pk=first.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with transaction.atomic():
            services.refresh_reservations(Book.objects.select_for_update().get(pk=book.pk))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, Reservation.Status.EXPIRED)
        self.assertEqual(second.status, Reservation.Status.READY)
        services.cancel_reservation(second.pk, reader3.pk)
        services.issue_to_reader(book.pk, self.reader2.pk, timezone.localdate())

    def test_cannot_reserve_available_or_already_borrowed_book(self):
        with self.assertRaises(ValidationError):
            services.reserve_for_reader(self.book.pk, self.reader2.pk)
        with self.assertRaises(ValidationError):
            services.reserve_for_reader(self.book.pk, self.reader1.pk)

    def test_student_cannot_cancel_another_readers_reservation(self):
        book, _ = self.unavailable_book()
        reservation = services.reserve_for_reader(book.pk, self.reader2.pk)
        self.client.force_login(self.user1)
        self.assertEqual(self.client.post(reverse('reservation_cancel', args=[reservation.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('reserve_book', args=[book.pk])).status_code, 405)

    def test_held_copy_is_not_advertised_as_available(self):
        book, loan = self.unavailable_book()
        services.reserve_for_reader(book.pk, self.reader2.pk)
        services.return_loan(loan.pk)
        response = self.client.get(reverse('books'), {'q': book.title, 'availability': 'available'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.client.force_login(self.user1)
        response = self.client.get(reverse('books'), {'q': book.title, 'availability': 'unavailable'})
        self.assertContains(response, 'Reserved')
        self.assertContains(response, 'Reserve this book')

    def test_inactive_account_cannot_reserve_and_releases_its_hold(self):
        book, loan = self.unavailable_book()
        reservation = services.reserve_for_reader(book.pk, self.reader2.pk)
        get_user_model().objects.filter(pk=self.user2.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            services.reserve_for_reader(book.pk, self.reader2.pk)
        services.return_loan(loan.pk)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertIsNone(reservation.active_slot)

    def test_archived_and_inactive_readers_cannot_borrow(self):
        Student.objects.filter(pk=self.reader2.pk).update(is_archived=True)
        with self.assertRaises(ValidationError):
            services.issue_to_reader(self.book.pk, self.reader2.pk, timezone.localdate())

    def test_reminders_are_idempotent_and_dry_run_changes_nothing(self):
        IssueBook.objects.filter(pk=self.loan.pk).update(due_date=timezone.localdate() - timedelta(days=1), issue_date=timezone.localdate() - timedelta(days=15))
        call_command('send_reminders', dry_run=True, stdout=StringIO())
        self.assertEqual(ReminderLog.objects.count(), 0)
        call_command('send_reminders', stdout=StringIO())
        call_command('send_reminders', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(ReminderLog.objects.filter(sent_at__isnull=False).count(), 1)
        self.assertIn('overdue', mail.outbox[0].body)

    def test_staff_pages_render_with_shared_theme(self):
        self.as_staff()
        for name in ['home', 'books', 'students', 'loans', 'reservations', 'book_add', 'student_add', 'about', 'contact', 'password_change']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'id="theme-toggle"')

    def test_header_uses_reader_name_and_secure_account_menu(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('books'))
        self.assertContains(response, f'Account menu for {self.reader1.student_name}')
        self.assertContains(response, 'aria-label="Breadcrumb"')
        self.assertContains(response, 'Change password')
        self.assertContains(response, f'method="post" action="{reverse("logout")}"')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertNotContains(response, self.reader2.student_name)

    def test_guest_header_shows_login_without_account_menu(self):
        response = self.client.get(reverse('books'))
        self.assertContains(response, 'Join library')
        self.assertNotContains(response, 'data-account-menu')

    def test_empty_dashboard_and_catalogue_render(self):
        self.as_staff()
        services.return_loan(self.loan.pk)
        services.archive_book(self.book.pk)
        self.assertContains(self.client.get(reverse('home')), 'A new chapter is coming')
        self.assertContains(self.client.get(reverse('books')), 'No books found')


@skipUnlessDBFeature('has_select_for_update')
class MySQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.book = make_book(quantity=1, available_copies=1)
        self.readers = [make_student(11), make_student(12)]

    def run_concurrently(self, action):
        barrier = Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                action(index)
                return 'ok'
            except ValidationError:
                return 'rejected'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, [0, 1]))

    def test_two_borrowers_cannot_take_the_last_copy(self):
        results = self.run_concurrently(lambda index: services.issue_to_reader(self.book.pk, self.readers[index].pk, timezone.localdate()))
        self.assertCountEqual(results, ['ok', 'rejected'])
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 0)
        self.assertEqual(IssueBook.objects.filter(returned_status=False).count(), 1)

    def test_simultaneous_returns_update_inventory_once(self):
        loan = services.issue_to_reader(self.book.pk, self.readers[0].pk, timezone.localdate())
        results = self.run_concurrently(lambda _: services.return_loan(loan.pk))
        self.assertCountEqual(results, ['ok', 'rejected'])
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)

    def test_simultaneous_duplicate_reservations_are_rejected(self):
        services.issue_to_reader(self.book.pk, self.readers[0].pk, timezone.localdate())
        results = self.run_concurrently(lambda _: services.reserve_for_reader(self.book.pk, self.readers[1].pk))
        self.assertCountEqual(results, ['ok', 'rejected'])
        self.assertEqual(Reservation.objects.filter(active_slot=1).count(), 1)
