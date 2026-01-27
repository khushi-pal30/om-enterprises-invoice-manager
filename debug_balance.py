import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'om_invoice_manager.settings')
django.setup()

from dashboard.models import Invoice
from decimal import Decimal

# Get all invoices
invoices = Invoice.objects.all()
print("=== INVOICE BALANCE DEBUG ===")
for inv in invoices:
    print(f"\nInvoice: {inv.invoice_number}")
    print(f"Contract Amount: ₹{inv.contract_amount}")
    print(f"Paid Amount: ₹{inv.paid_amount}")
    print(f"TDS Amount: ₹{inv.tds_amount}")
    print(f"Other Deductions: ₹{inv.other_deductions}")
    print(f"Retention Amount: ₹{inv.retention_amount}")
    print(f"Retention Released: {inv.retention_released}")
    print(f"Certified Amount (model): ₹{inv.certified_amount}")
    print(f"Total Received (model): ₹{inv.total_received}")

    # Manual calculation
    gst = (inv.contract_amount * (inv.cgst_percent + inv.sgst_percent) / 100)
    certified_manual = inv.contract_amount + gst - inv.other_deductions
    if not inv.retention_released:
        certified_manual -= inv.retention_amount
    total_received_manual = inv.paid_amount - inv.tds_amount
    if inv.retention_released:
        total_received_manual += inv.retention_amount
    else:
        total_received_manual -= inv.retention_amount
    balance_manual = certified_manual - total_received_manual

    print(f"Certified Amount (manual): ₹{certified_manual}")
    print(f"Total Received (manual): ₹{total_received_manual}")
    print(f"Balance Due (manual): ₹{balance_manual}")
