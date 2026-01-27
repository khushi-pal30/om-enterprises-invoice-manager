from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import Invoice, CompanySettings, Project, Client
from django.utils import timezone

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'client',
            'project_name',
            'work_order_no',
            'contract_amount',
            'retention_percent',
            'gst_percent',
            'start_date',
            'end_date',
            'scope_of_work',
            'project_manager',
            'status',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'scope_of_work': forms.Textarea(attrs={'rows': 3}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'name',
            'phone',
            'email',
            'address',
            'gst_number',
            'pan_number',
            'contact_person',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class InvoiceForm(forms.ModelForm):
    total_amount = forms.DecimalField(
        max_digits=14, decimal_places=2,
        required=False, disabled=True,
        label='Total Amount (After Deductions)'
    )

    value_of_work_done = forms.DecimalField(
        max_digits=14, decimal_places=2,
        required=False, disabled=True,
        label='Value of Work Done'
    )



    mark_as_paid = forms.BooleanField(required=False, label="Mark as Paid")

    class Meta:
        model = Invoice
        fields = [
            'invoice_date',
            'invoice_number',
            'project',
            'ra_bill_no',
            'contract_amount',
            'cgst_percent',
            'sgst_percent',
            'retention_type',
            'retention_percent',
            'retention_fixed_amount',
            'retention_due_date',
            'tds_amount',
            'payment_mode',
            'paid_amount',
            'due_date',
            'payment_date',
            'other_deductions',
            'tds_verified',
            'tds_verified_date',
        ]
        widgets = {
            'invoice_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'retention_type': forms.Select(
                attrs={'class': 'form-control', 'id': 'retention_type'}
            ),
            'retention_percent': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'id': 'retention_percent'}
            ),
            'retention_fixed_amount': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'id': 'retention_fixed'}
            ),
            'due_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'retention_due_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'payment_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'tds_verified_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['total_amount'].initial = self.instance.certified_amount

# -------------------------
# Company Settings Form
# -------------------------
class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = CompanySettings
        fields = ['company_name', 'email', 'phone', 'address', 'invoice_prefix', 'invoice_footer']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'invoice_footer': forms.Textarea(attrs={'rows': 2}),
        }

# -------------------------
# Admin Password Change Form
# -------------------------
class AdminPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control'}))
