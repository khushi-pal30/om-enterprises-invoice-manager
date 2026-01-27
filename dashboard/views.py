
import csv
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q ,F, ExpressionWrapper, DecimalField, Case, When, Value
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.utils import timezone
from .models import Client, Project, Invoice, CompanySettings, Payment
from .forms import ProjectForm, InvoiceForm, CompanySettingsForm, AdminPasswordChangeForm, ClientForm
from .utils import generate_gst_invoice
from .email_service import send_invoice_email
from .whatsapp_service import send_whatsapp_invoice
from django.contrib.auth import update_session_auth_hash
from django.db.models import F, Sum
from decimal import Decimal, ROUND_HALF_UP

# -------------------------
# DASHBOARD
# -------------------------
@login_required
def dashboard_view(request):
    if not request.user.is_superuser:
        return redirect('/admin/login/')

    if request.method == 'POST' and 'reset_data' in request.POST:
        # Handle data reset
        Invoice.objects.all().delete()
        Project.objects.all().delete()
        Client.objects.all().delete()
        CompanySettings.objects.all().delete()
        messages.success(request, "All data has been reset successfully.")
        return redirect('dashboard')

    total_contract = Project.objects.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0

    invoices_paid = Invoice.objects.filter(status='Paid')
    invoices_pending = Invoice.objects.exclude(status='Paid')
    
    paid_amount = sum(inv.total_received for inv in invoices_paid)
    pending_amount = sum(inv.certified_amount for inv in invoices_pending)
    paid_percentage = (paid_amount / total_contract * 100) if total_contract else 0

    # GST & Net Profit
    gst_collected = sum((inv.total_tax_amount for inv in invoices_paid))
    net_profit = sum((inv.certified_amount - inv.total_tax_amount for inv in invoices_paid))

    # Total Balance Due
    total_balance_due = sum(
        inv.certified_amount - inv.total_received - inv.tds_amount
        for inv in Invoice.objects.all()
    )

    # Monthly sales
    month_map = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    monthly_data = {}
    for inv in Invoice.objects.all():
        if inv.invoice_date:
            key = f"{month_map[inv.invoice_date.month]} {inv.invoice_date.year}"
            monthly_data[key] = monthly_data.get(key, 0) + float(inv.certified_amount)

    # Project-wise pending breakdown
    projects_breakdown = []
    search_query = request.GET.get('project_search', '')
    financial_year = request.GET.get('financial_year', '')

    projects_qs = Project.objects.select_related('client').prefetch_related('invoices')

    if search_query:
        projects_qs = projects_qs.filter(
            Q(project_name__icontains=search_query) |
            Q(client__name__icontains=search_query)
        )

    for project in projects_qs:
        invoices = project.invoices.all()
        if financial_year:
            fy_start = int(financial_year.split('-')[0])
            fy_end = fy_start + 1
            invoices = invoices.filter(invoice_date__year__gte=fy_start, invoice_date__year__lt=fy_end)

        paid_invoices = invoices.filter(status='Paid')
        pending_invoices = invoices.exclude(status='Paid')

        paid_total = sum(inv.certified_amount for inv in paid_invoices)
        pending_total = sum(inv.certified_amount for inv in pending_invoices)
        balance_due_total = sum(inv.certified_amount - inv.total_received - inv.tds_amount for inv in invoices  )

        latest_invoice = invoices.order_by('-id').first()
        inv_id = latest_invoice.invoice_number if latest_invoice else 'N/A'

        projects_breakdown.append({
            'project_name': project.project_name,
            'client_name': project.client.name,
            'paid': round(paid_total, 2),
            'pending': round(pending_total, 2),
            'balance_due': round(balance_due_total, 2),
            'inv_id': inv_id,
        })

    # Financial year options
    current_year = timezone.now().year
    financial_years = [f"{year}-{year+1}" for year in range(current_year-5, current_year+1)]

    context = {
        'total_contract': round(total_contract, 2),
        'paid_amount': round(paid_amount, 2),
        'pending_amount': round(pending_amount, 2),
        'paid_percentage': round(paid_percentage, 2),
        'gst_collected': round(gst_collected, 2),
        'net_profit': round(net_profit, 2),
        'total_balance_due': round(total_balance_due, 2),
        'months': list(monthly_data.keys()),
        'monthly_sales': list(monthly_data.values()),
        'projects_breakdown': projects_breakdown,
        'search_query': search_query,
        'financial_year': financial_year,
        'financial_years': financial_years,
    }
    return render(request, 'dashboard.html', context)


# -------------------------
# ADD PROJECT
# -------------------------
@login_required
def add_project(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Project added successfully")
            return redirect("projects")
        else:
            messages.error(request, "Please correct the errors below")

    else:
        form = ProjectForm()

    return render(request, "add_project.html", {"form": form})


# -------------------------
# ADD CLIENT
# -------------------------
@login_required
def add_client(request):
    if not request.user.is_superuser:
        return redirect('/admin/login/')

    clients = Client.objects.all()

    if request.method == "POST":
        form = ClientForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Client added successfully")
            return redirect("clients")
        else:
            messages.error(request, "Please correct the errors below")

    else:
        form = ClientForm()

    return render(request, "clients.html", {"form": form, "clients": clients})


# -------------------------
# EDIT CLIENT
# -------------------------
@login_required
def edit_client(request, client_id):
    if not request.user.is_superuser:
        return redirect('/admin/login/')

    client = get_object_or_404(Client, id=client_id)

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client updated successfully")
            return redirect("clients")
        else:
            messages.error(request, "Please correct the errors below")
    else:
        form = ClientForm(instance=client)

    return render(request, "clients.html", {"form": form, "clients": Client.objects.all(), "edit_client": client})


# -------------------------
# DELETE CLIENT
# -------------------------
@login_required
def delete_client(request, client_id):
    if not request.user.is_superuser:
        return redirect('/admin/login/')

    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        client.delete()
        messages.success(request, "Client deleted successfully")
        return redirect('clients')

    return render(request, 'clients.html', {'delete_client': client, 'clients': Client.objects.all()})




# -------------------------
# EDIT PROJECT
# -------------------------
@login_required
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated successfully")
            return redirect('projects')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'project_edit.html', {'form': form, 'project': project})


# -------------------------
# DELETE PROJECT
# -------------------------
@login_required
def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted successfully")
        return redirect('projects')
    return render(request, 'project_delete.html', {'project': project})


# -------------------------
# LIST PROJECTS
# -------------------------
@login_required
def projects(request):
    projects = Project.objects.select_related('client').all()
    search_query = request.GET.get('q')
    if search_query:
        projects = projects.filter(
            Q(project_name__icontains=search_query) |
            Q(client__name__icontains=search_query)
        )

    context = {
        'projects': projects,
        'total_projects': projects.count(),
        'completed': projects.filter(status='Completed').count(),
        'active': projects.filter(status='Active').count(),
        'pending': projects.filter(status='Pending').count(),
    }
    return render(request, 'projects.html', context)


# -------------------------
# ADD INVOICE
# -------------------------
@login_required
def add_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            if form.cleaned_data['mark_as_paid']:
                invoice.status = 'Paid'
            invoice.save()
            messages.success(request, "Invoice added successfully")
            return redirect('invoices')
    else:
        form = InvoiceForm()
    return render(request, 'add_invoice.html', {'form': form})


# -------------------------
# EDIT INVOICE
# -------------------------
@login_required
def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            invoice = form.save(commit=False)
            if form.cleaned_data['mark_as_paid']:
                invoice.status = 'Paid'
            invoice.save()
            messages.success(request, "Invoice updated successfully")
            return redirect('invoices')
    else:
        form = InvoiceForm(instance=invoice)
    return render(request, 'edit_invoice.html', {'form': form, 'invoice': invoice})


# -------------------------
# DELETE INVOICE
# -------------------------
@login_required
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, "Invoice deleted successfully")
        return redirect('invoices')
    return render(request, 'invoice_delete.html', {'invoice': invoice})


# -------------------------
# LIST INVOICES
# -------------------------
@login_required
def invoices(request):
    invoices = Invoice.objects.select_related(
        'project', 'project__client'
    )

    search_query = request.GET.get('q')
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(project__project_name__icontains=search_query) |
            Q(project__client__name__icontains=search_query)
        )

    # ORM expressions for retention and certified amount
    invoices = invoices.annotate(
        pending_amount_calc=ExpressionWrapper(
            F('contract_amount') - F('paid_amount'),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        retention_amount_calc=Case(
            When(retention_type='percent', then=F('contract_amount') * F('retention_percent') / 100),
            When(retention_type='amount', then=F('retention_fixed_amount')),
            default=0,
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        certified_amount_calc=ExpressionWrapper(
                F('contract_amount')
            + (F('contract_amount') * (F('cgst_percent') + F('sgst_percent')) / 100) - F('other_deductions'),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        total_received_calc=ExpressionWrapper(
            F('paid_amount') - F('tds_amount') + F('retention_amount_calc') * (2 * F('retention_released') - 1),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        balance_due_calc=ExpressionWrapper(
            F('certified_amount_calc') - F('total_received_calc')-F('tds_amount'),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        total_tax_amount_calc=ExpressionWrapper(
            F('pending_amount_calc') * (F('cgst_percent') + F('sgst_percent')) / 100,
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
    )
    tds_pending_invoices = invoices.filter(
        tds_amount__gt=0,
        tds_verified=False
    )

    retention_hold_invoices = invoices.filter(
        retention_amount_calc__gt=0,
        retention_released=False
    )

    retention_overdue_invoices = invoices.filter(
        retention_amount_calc__gt=0,
        retention_due_date__lt=timezone.now().date(),
        retention_released=False
    ).exclude(retention_due_date__isnull=True)

    retention_released_invoices = invoices.filter(
        retention_amount_calc__gt=0,
        retention_released=True
    )

    overdue_invoices = invoices.filter(
        due_date__lt=timezone.now().date(),
        status='Pending'
    ).exclude(due_date__isnull=True)

    pending_invoices = invoices.filter(status='Pending')

    balance_due_invoices = invoices.filter(balance_due_calc__gt=0)

    balance_due = invoices.aggregate(
        total=Sum('balance_due_calc')
    )['total'] or 0

    pending_amount = invoices.aggregate(
        total=Sum('pending_amount_calc')
    )['total'] or 0

    context = {
        'invoices': invoices.order_by('-id'),
        'total_invoices': invoices.count(),
        'paid': invoices.filter(status='Paid').count(),
        'pending': invoices.exclude(status='Paid').count(),

        'total_invoice_amount': invoices.aggregate(
            total=Sum('certified_amount_calc')
        )['total'] or 0,

        'total_received_amount': invoices.aggregate(
            total=Sum('total_received_calc')
        )['total'] or 0,

        'balance_due': balance_due,
        'pending_amount': pending_amount,

        'total_tds_pending': tds_pending_invoices.aggregate(
            total=Sum('tds_amount')
        )['total'] or 0,
        
        'total_retention_amount': invoices.aggregate(
            total=Sum('retention_amount_calc')
        )['total'] or 0,

        'total_retention_hold': retention_hold_invoices.aggregate(
            total=Sum('retention_amount_calc')
        )['total'] or 0,

        'total_retention_released': retention_released_invoices.aggregate(
            total=Sum('retention_amount_calc')
        )['total'] or 0,

        'tds_pending_invoices': tds_pending_invoices,
        'retention_hold_invoices': retention_hold_invoices,
        'retention_overdue_invoices': retention_overdue_invoices,
        'retention_released_invoices': retention_released_invoices,
        'overdue_invoices': overdue_invoices,
        'total_overdue': overdue_invoices.count(),
        'total_retention_overdue': retention_overdue_invoices.count(),
        'pending_invoices': pending_invoices,
        'balance_due_invoices': balance_due_invoices,
    }

    return render(request, 'invoices.html', context)






# -------------------------
# SEND INVOICE
# -------------------------
@login_required
def send_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    try:
        pdf_path = generate_gst_invoice(invoice)
        send_invoice_email(invoice, pdf_path)
        # send_whatsapp_invoice(invoice.project.client.phone, invoice.certified_amount)
        invoice.status = 'Paid'
        invoice.save()
        messages.success(request, "Invoice sent and marked as Paid.")
    except Exception as e:
        messages.error(request, f"Failed to send invoice: {e}")
    return redirect('invoices')


# -------------------------
# PAY RETENTION
# -------------------------
@login_required
def pay_retention(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        payment_amount = Decimal(request.POST.get('payment_amount', 0))
        payment_date = request.POST.get('payment_date')
        payment_mode = request.POST.get('payment_mode')
        remaining_retention = invoice.retention_amount - invoice.retention_paid_amount
        if payment_amount > 0 and payment_amount <= remaining_retention:
            # Store the payment amount in session for the receipt
            request.session['last_payment_amount'] = str(payment_amount)
            previous_paid = invoice.paid_amount
            invoice.paid_amount += payment_amount
            invoice.payment_date = payment_date
            invoice.retention_paid_amount += payment_amount
            if invoice.retention_paid_amount >= invoice.retention_amount:
                invoice.retention_released = True  # Mark retention as released only if full retention is paid
                invoice.retention_released_date = payment_date
            invoice.save()

            # Create Payment record
            Payment.objects.create(
                invoice=invoice,
                amount=payment_amount,
                payment_date=payment_date,
                payment_mode=payment_mode
            )

            messages.success(request, f"Retention payment of ₹{payment_amount} recorded successfully.")
            # Redirect to payment receipt
            return redirect('payment_receipt', invoice_id=invoice.id)
        else:
            messages.error(request, "Invalid payment amount.")
    return redirect('invoices')


# -------------------------
# DOWNLOAD INVOICE PDF
# -------------------------
@login_required
def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    template = get_template('invoice_pdf.html')
    gst_percent = invoice.cgst_percent + invoice.sgst_percent
    grand_total = round(invoice.certified_amount + invoice.total_tax_amount, 2)
    balance_due = round(invoice.certified_amount - invoice.total_received- invoice.tds_amount, 2)
    html = template.render({
        'invoice': invoice,
        'cgst_amount': round(invoice.cgst_amount, 2),
        'sgst_amount': round(invoice.sgst_amount, 2),
        'total_tax': round(invoice.total_tax_amount, 2),
        'grand_total': grand_total,
        'certified_amount': round(invoice.certified_amount, 2),
        'gst_percent': gst_percent,
        'balance_due': balance_due
    })
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_number}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


# -------------------------
# EXPORT CSV
# -------------------------
@login_required
def export_data(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    writer = csv.writer(response)
    writer.writerow(['Invoice No', 'Client', 'Project', 'Certified Amount', 'Status'])
    for inv in Invoice.objects.select_related('project', 'project__client').all():
        writer.writerow([
            inv.invoice_number,
            inv.project.client.name,
            inv.project.project_name,
            round(inv.certified_amount, 2),
            inv.status
        ])
    return response


# -------------------------
# CLIENTS PAGE
# -------------------------
@login_required
def clients_page(request):
    clients = Client.objects.all()
    return render(request, 'clients.html', {'clients': clients})


# -------------------------
# SETTINGS PAGE
# -------------------------
@login_required
def settings(request):
    settings = CompanySettings.objects.first()
    if not settings:
        settings = CompanySettings.objects.create(company_name="")

    if request.method == 'POST':
        if 'save_company' in request.POST:
            form = CompanySettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                messages.success(request, "Company settings saved.")
                return redirect('settings')
        elif 'change_password' in request.POST:
            pwd_form = AdminPasswordChangeForm(request.user, request.POST)
            if pwd_form.is_valid():
                user = pwd_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('settings')
    else:
        form = CompanySettingsForm(instance=settings)
        pwd_form = AdminPasswordChangeForm(request.user)

    return render(request, 'settings.html', {'form': form, 'pwd_form': pwd_form})
# -------------------------
# MARK INVOICE AS PAID
# -------------------------
@login_required
def mark_invoice_paid(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.status != "Paid":
        invoice.status = "Paid"
        invoice.save()
        messages.success(request, "Invoice marked as Paid.")
    else:
        messages.warning(request, "Invoice is already Paid.")
    return redirect('invoices')

@login_required
def make_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        payment_amount = Decimal(request.POST.get('payment_amount', 0))
        payment_date = request.POST.get('payment_date')
        payment_mode = request.POST.get('payment_mode')
        pay_retention = request.POST.get('pay_retention') == 'on'
        # Calculate balance due as certified - total_received
        balance_due = invoice.certified_amount - invoice.total_received
        if pay_retention:
            remaining_retention = invoice.retention_amount - invoice.retention_paid_amount
            max_allowed = remaining_retention
        else:
            max_allowed = balance_due
        if payment_amount > 0 and payment_amount <= max_allowed:
            # Store the payment amount in session for the receipt
            request.session['last_payment_amount'] = str(payment_amount)
            previous_paid = invoice.paid_amount
            invoice.paid_amount += payment_amount
            invoice.payment_date = payment_date
            if pay_retention:
                invoice.retention_paid_amount += payment_amount
                if invoice.retention_paid_amount >= invoice.retention_amount:
                    invoice.retention_released = True
                    invoice.retention_released_date = payment_date
            invoice.save()

            # Create Payment record
            Payment.objects.create(
                invoice=invoice,
                amount=payment_amount,
                payment_date=payment_date,
                payment_mode=payment_mode
            )

            messages.success(request, f"Payment of ₹{payment_amount} recorded successfully.")
            # Redirect to payment receipt
            return redirect('payment_receipt', invoice_id=invoice.id)
        else:
            messages.error(request, "Invalid payment amount.")
    return redirect('invoices')

@login_required
def view_reports(request):
    # Overall project summary metrics
    total_clients = Client.objects.count()
    total_projects = Project.objects.count()
    total_contract_value = Project.objects.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0
    total_invoices = Invoice.objects.count()

    # Annotate invoices with certified_amount_calc
    invoices_qs = Invoice.objects.annotate(
        certified_amount_calc=ExpressionWrapper(
            F('contract_amount') + (F('contract_amount') * (F('cgst_percent') + F('sgst_percent')) / 100),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        )
    )

    # Total invoiced amount (sum of certified amounts)
    total_invoiced_amount = invoices_qs.aggregate(
        total=Sum('certified_amount_calc')
    )['total'] or 0
    # TDS amount (sum of TDS amounts)
    tds_amount = invoices_qs.aggregate(
        total=Sum('tds_amount')
    )['total'] or 0
    # Received amount (sum of total received amounts)
    received_amount = Invoice.objects.annotate(
        retention_amount_calc=Case(
            When(retention_type='percent', then=F('contract_amount') * F('retention_percent') / 100),
            When(retention_type='amount', then=F('retention_fixed_amount')),
            default=0,
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        total_received=ExpressionWrapper(
            F('paid_amount') - F('tds_amount') + F('retention_amount_calc') * Case(
                When(retention_released=True, then=1),
                default=0,
                output_field=DecimalField(max_digits=14, decimal_places=4)
            ),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        )
    ).aggregate(
        total=Sum('total_received')
    )['total'] or 0

    # Overdue amount (invoices past due date and not paid)
    overdue_invoices = invoices_qs.filter(
        due_date__lt=timezone.now().date(),
        status__in=['Pending', 'Sent']
    )
    overdue_amount = overdue_invoices.aggregate(
        total=Sum('certified_amount_calc')
    )['total'] or 0

    # Due amount (total invoiced - received)
    due_amount = total_invoiced_amount - received_amount - tds_amount

    context = {
        'total_clients': total_clients,
        'total_projects': total_projects,
        'total_contract_value': round(total_contract_value, 2),
        'total_invoices': total_invoices,
        'total_invoiced_amount': round(total_invoiced_amount, 2),
        'received_amount': round(received_amount, 2),
        'overdue_amount': round(overdue_amount, 2),
        'due_amount': round(due_amount, 2),
    }
    return render(request, 'reports.html', context)

@login_required
def invoice_preview(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    gst_amount = round(invoice.total_tax_amount, 2)
    grand_total = round(invoice.certified_amount + invoice.total_tax_amount, 2)
    balance = round(invoice.certified_amount - invoice.paid_amount-invoice.tds_amount, 2)
    certified_amount = round(invoice.certified_amount, 2)
    gst_percent = invoice.cgst_percent + invoice.sgst_percent
    total_received = round(invoice.total_received, 2)
    return render(request, 'invoice_preview.html', {
        'invoice': invoice,
        'gst_amount': gst_amount,
        'grand_total': grand_total,
        'balance': balance,
        'certified_amount': certified_amount,
        'gst_percent': gst_percent,
        'total_received': round(invoice.total_received, 2),
    })

@login_required
def payment_receipt(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    # Get the latest payment amount from session
    payment_amount = Decimal(request.session.get('last_payment_amount', '0'))
    # Clear the session after use
    if 'last_payment_amount' in request.session:
        del request.session['last_payment_amount']

    gst_amount = round(invoice.total_tax_amount, 2)
    grand_total = round(invoice.certified_amount + invoice.total_tax_amount, 2)
    balance_due = round(invoice.certified_amount - invoice.total_received -invoice.tds_amount, 2)

    # Calculate previous payments (total paid minus current payment)
    previous_payments = round(invoice.paid_amount - payment_amount, 2)

    context = {
        'invoice': invoice,
        'payment_amount': payment_amount,
        'payment_date': invoice.payment_date,
        'gst_amount': gst_amount,
        'grand_total': grand_total,
        'balance_due': balance_due,
        'certified_amount': round(invoice.certified_amount, 2),
        'gst_percent': invoice.cgst_percent + invoice.sgst_percent,
        'previous_payments': previous_payments,
    }
    return render(request, 'payment_receipt.html', context)
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    invoices = project.invoices.annotate(
        retention_amount_calc=Case(
            When(retention_type='percent', then=F('contract_amount') * F('retention_percent') / 100),
            When(retention_type='amount', then=F('retention_fixed_amount')),
            default=0,
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        certified_amount_calc=ExpressionWrapper(
            F('contract_amount') + (F('contract_amount') * (F('cgst_percent') + F('sgst_percent')) / 100) - F('other_deductions') - F('retention_amount_calc') * (1 - F('retention_released')),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        total_received_calc=ExpressionWrapper(
           F('paid_amount') - F('tds_amount') + F('retention_amount_calc') * (2 * F('retention_released') - 1),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
        balance_due_calc=ExpressionWrapper(
            F('certified_amount_calc') - F('total_received_calc')-F('tds_amount'),
            output_field=DecimalField(max_digits=14, decimal_places=4)
        ),
    ).order_by('invoice_date')

    # Calculate total paid amount for the project
    total_paid = invoices.aggregate(
        total=Sum('total_received_calc')
    )['total'] or 0

    # Calculate balance due for the project
    balance_due = invoices.aggregate(
        total=Sum('balance_due_calc')
    )['total'] or 0

    return render(request, 'project_detail.html', {
        'project': project,
        'invoices': invoices,
        'total_paid': total_paid,
        'balance_due': balance_due
    })
def verify_tds(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if invoice.tds_amount > 0 and not invoice.tds_verified:
        invoice.tds_verified = True
        invoice.tds_verified_date = timezone.now().date()
        # ❌ tds_amount ko touch mat karo
        invoice.save(update_fields=['tds_verified', 'tds_verified_date'])

    return redirect('invoices')



# -------------------------
# PAYMENT HISTORY
# -------------------------
@login_required
def payment_history(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    payments = Payment.objects.filter(invoice=invoice).order_by('payment_date')

    # Get date filters from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Apply date filters if provided
    if start_date:
        payments = payments.filter(payment_date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__lte=end_date)

    # Calculate running total for filtered payments
    running_total = Decimal('0')
    payment_data = []

    # If there are no Payment records but invoice has paid_amount, show it as initial payment (only if no filters or if it matches)
    if not payments.exists() and invoice.paid_amount > 0 and not (start_date or end_date):
        payment_data.append({
            'date': invoice.payment_date or invoice.invoice_date,
            'amount': invoice.paid_amount,
            'mode': invoice.get_payment_mode_display(),
            'running_total': invoice.paid_amount,
            'notes': 'Initial payment'
        })
        running_total = invoice.paid_amount
    else:
        # Show individual payment records
        for payment in payments:
            running_total += payment.amount
            payment_data.append({
                'date': payment.payment_date,
                'amount': payment.amount,
                'mode': payment.payment_mode,
                'running_total': running_total,
                'notes': payment.notes or ''
            })

    # Calculate correct balance remaining (always based on full invoice)
    balance_remaining = invoice.certified_amount - invoice.total_received- invoice.tds_amount

    context = {
        'invoice': invoice,
        'payment_data': payment_data,
        'total_payments': len(payment_data),
        'total_amount_paid': running_total,  # Sum of filtered payments
        'balance_remaining': max(Decimal('0'), balance_remaining),  # Ensure not negative
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'payment_history.html', context)


# -------------------------
# GLOBAL SEARCH
# -------------------------
@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    clients = []
    projects = []
    invoices = []

    if query:
        # Search clients
        clients = Client.objects.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(address__icontains=query)
        )

        # Search projects
        projects = Project.objects.select_related('client').filter(
            Q(project_name__icontains=query) |
            Q(client__name__icontains=query) |
            Q(scope_of_work__icontains=query)
        )

        # Search invoices
        invoices = Invoice.objects.select_related('project', 'project__client').filter(
            Q(invoice_number__icontains=query) |
            Q(project__project_name__icontains=query) |
            Q(project__client__name__icontains=query)
        )

    context = {
        'query': query,
        'clients': clients,
        'projects': projects,
        'invoices': invoices,
        'total_results': len(clients) + len(projects) + len(invoices)
    }

    return render(request, 'search_results.html', context)
