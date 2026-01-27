from reportlab.pdfgen import canvas
from django.conf import settings
import os
from decimal import Decimal
def generate_gst_invoice(invoice):
    # Safe fallback values
    project_name = invoice.project.project_name if invoice.project else "N/A"
    client_name = (
        invoice.project.client.name
        if invoice.project and invoice.project.client
        else "N/A"
    )

    # Ensure media/invoices folder exists
    invoice_folder = os.path.join(settings.BASE_DIR, 'media', 'invoices')
    os.makedirs(invoice_folder, exist_ok=True)

    # ✅ FIXED FIELD NAME
    path = os.path.join(
        invoice_folder,
        f"OM_Invoice_{invoice.invoice_number}.pdf"
    )

    c = canvas.Canvas(path)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 820, "OM ENTERPRISES")
    c.setFont("Helvetica", 11)
    c.drawString(50, 800, "Builder & Construction Services")
    c.line(50, 790, 550, 790)

    # Invoice Info
    c.drawString(50, 760, f"Invoice No: {invoice.invoice_number}")
    c.drawString(50, 740, f"Client: {client_name}")
    c.drawString(50, 720, f"Project: {project_name}")

    # Updated to use new fields
    base_amount = invoice.certified_amount
    gst_percent = invoice.cgst_percent + invoice.sgst_percent
    gst_amount = invoice.total_tax_amount
    grand_total = invoice.certified_amount + gst_amount
    balance = grand_total - invoice.paid_amount

    c.drawString(50, 680, f"Base Amount: ₹{base_amount}")
    c.drawString(50, 660, f"GST ({gst_percent}%): ₹{gst_amount}")
    c.drawString(50, 640, f"Total Amount: ₹{grand_total}")
    c.drawString(50, 620, f"Paid Amount: ₹{invoice.paid_amount}")
    c.drawString(50, 600, f"Balance Due: ₹{balance}")

    c.drawString(50, 560, "Authorized Signatory")
    c.drawString(50, 540, "Om Enterprises")

    c.save()
    return path

