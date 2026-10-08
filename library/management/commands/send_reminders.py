from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from library.models import Book, IssueBook, ReminderLog, Reservation
from library.services import refresh_reservations

class Command(BaseCommand):
    help = 'Send due/overdue and reservation-ready emails. Schedule daily; use --dry-run to preview.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        today = timezone.localdate()
        if not options['dry_run']:
            book_ids = Reservation.objects.filter(active_slot=1).values_list('book_id', flat=True).distinct()
            for book_id in book_ids:
                with transaction.atomic():
                    book = Book.objects.select_for_update().get(pk=book_id)
                    refresh_reservations(book)
        due = list(IssueBook.objects.filter(returned_status=False, due_date__lte=today + timedelta(days=1)).select_related('book', 'student'))
        ready = list(Reservation.objects.filter(status=Reservation.Status.READY, active_slot=1, expires_at__gt=timezone.now()).select_related('book', 'student'))
        if options['dry_run']:
            self.stdout.write(f'Dry run: {len(due)} due/overdue loans and {len(ready)} ready reservations. No emails sent or records changed.')
            return
        sent = skipped = failed = 0
        for item in due + ready:
            is_loan = isinstance(item, IssueBook)
            kind = ('overdue' if item.is_overdue else 'due') if is_loan else 'ready'
            day = today if is_loan else timezone.localtime(item.ready_at).date()
            subject = f'Library reminder: {item.book.title}'
            body = (f'Hello {item.student.student_name},\n\nYour copy of {item.book.title} is {"overdue" if item.is_overdue else "due soon"}. Due date: {item.due_date:%d %b %Y}. Please contact the library about returning it.' if is_loan else f'Hello {item.student.student_name},\n\nYour reservation for {item.book.title} is ready. Please collect it by {timezone.localtime(item.expires_at):%d %b %Y %H:%M}.')
            try:
                with transaction.atomic():
                    log, _ = ReminderLog.objects.get_or_create(**{'loan' if is_loan else 'reservation': item}, kind=kind, day=day)
                    log = ReminderLog.objects.select_for_update().get(pk=log.pk)
                    if log.sent_at:
                        skipped += 1
                        continue
                    if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [item.student.email], fail_silently=False) != 1:
                        raise RuntimeError('Email backend did not accept the message.')
                    log.sent_at = timezone.now()
                    log.save(update_fields=['sent_at'])
                sent += 1
            except Exception:
                failed += 1
        self.stdout.write(f'Reminders: {sent} sent, {skipped} already sent, {failed} failed.')
        if failed:
            raise CommandError('Some messages failed. Check the SMTP configuration and retry; successful messages are recorded.')
