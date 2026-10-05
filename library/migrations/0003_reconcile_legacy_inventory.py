"""Preserve legacy records before adding inventory/date constraints."""
from datetime import timedelta
from django.db import migrations, models
from django.db.models import Count

def reconcile(apps, schema_editor):
    alias = schema_editor.connection.alias
    Book = apps.get_model('library', 'Book')
    Loan = apps.get_model('library', 'IssueBook')
    active = dict(Loan.objects.using(alias).filter(returned_status=False).values_list('book_id').annotate(total=Count('id')))
    for book in Book.objects.using(alias).all().iterator():
        if book.price < 0:
            raise RuntimeError('A legacy book has a negative price. Correct it before migrating.')
        count = active.get(book.pk, 0)
        book.quantity = max(book.quantity, count, 0)
        book.available_copies = book.quantity - count
        book.save(using=alias, update_fields=['quantity', 'available_copies'])
    for loan in Loan.objects.using(alias).all().iterator():
        loan.due_date = loan.issue_date + timedelta(days=14)
        if not loan.returned_status:
            loan.return_date = None
        elif loan.return_date and loan.return_date < loan.issue_date:
            raise RuntimeError('A legacy return date predates its issue date. Correct it before migrating.')
        loan.save(using=alias, update_fields=['due_date', 'return_date'])

class Migration(migrations.Migration):
    dependencies = [('library', '0002_alter_issuebook_return_date')]
    operations = [
        migrations.AddField(model_name='issuebook', name='due_date', field=models.DateField(null=True)),
        migrations.RunPython(reconcile, migrations.RunPython.noop),
        migrations.AlterField(model_name='issuebook', name='due_date', field=models.DateField()),
    ]
