from django.core.mail import EmailMessage
from decimal import Decimal
def send_invoice_email(invoice, pdf_path):
    base = Decimal(invoice.certified_amount)
    gst_percent = invoice.cgst_percent + invoice.sgst_percent
    gst = invoice.total_tax_amount
    grand_total = base + gst
    balance = grand_total - Decimal(invoice.paid_amount)

    mail = EmailMessage(
        subject=f"OM ENTERPRISES - GST Invoice {invoice.invoice_number}",
        body=f"""Dear {invoice.project.client.name},

Please find attached your GST invoice.

Invoice Number: {invoice.invoice_number}
Certified Amount: ₹{invoice.certified_amount}
GST ({gst_percent}%): ₹{gst}
Paid Amount: ₹{invoice.paid_amount}
Pending Amount: ₹{balance}

Regards,
Om Enterprises
""",
        to=[invoice.project.client.email]
    )

    mail.attach_file(pdf_path)
    mail.send()

