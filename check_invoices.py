import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'om_invoice_manager.settings')
django.setup()

from dashboard.models import Invoice
from django.utils import timezone

print("Total invoices:", Invoice.objects.count())

overdue = Invoice.objects.filter(
    due_date__lt=timezone.now().date(),
    status='Pending'
).exclude(due_date__isnull=True)
print("Overdue invoices:", overdue.count())

from django.db.models import Case, When, F, DecimalField
retention_overdue = Invoice.objects.annotate(
    retention_amount_calc=Case(
        When(retention_type='percent', then=F('contract_amount') * F('retention_percent') / 100),
        When(retention_type='amount', then=F('retention_fixed_amount')),
        default=0,
        output_field=DecimalField(max_digits=14, decimal_places=4)
    )
).filter(
    retention_amount_calc__gt=0,
    retention_released=False,
    retention_due_date__lt=timezone.now().date()
).exclude(retention_due_date__isnull=True)
print("Retention overdue:", retention_overdue.count())

# Check if retention_due_date is set for any invoices
invoices_with_retention_due_date = Invoice.objects.exclude(retention_due_date__isnull=True)
print("Invoices with retention_due_date set:", invoices_with_retention_due_date.count())

# Check if due_date is set for any invoices
invoices_with_due_date = Invoice.objects.exclude(due_date__isnull=True)
print("Invoices with due_date set:", invoices_with_due_date.count())
