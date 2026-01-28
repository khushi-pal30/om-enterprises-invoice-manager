
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
def two_dec(value):
    if value is None:
        value = Decimal('0')
    return Decimal(value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)


# =========================
# CLIENT
# =========================
class Client(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField(default="", blank=True)

    gst_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


# =========================
# PROJECT
# =========================
class Project(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    project_name = models.CharField(max_length=200)
    work_order_no = models.CharField(max_length=100, default="")

    contract_amount = models.DecimalField(
        max_digits=15, decimal_places=4, default=0
    )

    retention_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    gst_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=18
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    scope_of_work = models.TextField(default="", blank=True)
    project_manager = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('Active', 'Active'),
            ('Completed', 'Completed'),
            ('Pending', 'Pending'),
        ],
        default='Active'
    )

    def __str__(self):
        return self.project_name


# =========================
# INVOICE
# =========================



class Invoice(models.Model):

    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='invoices'
    )

    # ---------- RETENTION CONFIG ----------
    RETENTION_TYPE_CHOICES = (
        ('percent', 'Percentage (%)'),
        ('amount', 'Fixed Amount (₹)'),
    )

    retention_type = models.CharField(
        max_length=10,
        choices=RETENTION_TYPE_CHOICES,
        default='percent'
    )

    retention_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=5
    )

    retention_fixed_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )



    # ---------- BASIC DETAILS ----------
    invoice_number = models.CharField(max_length=50, unique=True)
    ra_bill_no = models.CharField(max_length=50, blank=True, null=True)

    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    retention_due_date = models.DateField(null=True, blank=True)
    # ---------- VALUES ----------
    contract_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    
    

    paid_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    # ---------- TAX ----------
    cgst_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=9
    )

    sgst_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=9
    )

    # ---------- DEDUCTIONS ----------
   
    

    tds_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    other_deductions = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    # ---------- PAYMENT MODE ----------
    PAYMENT_MODE_CHOICES = (
        ('bank', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
    )

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODE_CHOICES,
        default='bank'
    )

    payment_date = models.DateField(null=True, blank=True)
    last_payment_amount = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    # ---------- TDS VERIFY ----------
    tds_verified = models.BooleanField(default=False)
    tds_verified_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, default='Pending')

    # ---------- RETENTION RELEASE ----------
    retention_released = models.BooleanField(default=False)
    retention_released_date = models.DateField(null=True, blank=True)
    retention_paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # =====================================================
    # ================== COMPUTED PROPERTIES ==============
    # =====================================================


    def pending_amount(self):
        """Pending amount = contract_amount - paid_amount"""
        return two_dec(self.contract_amount - self.paid_amount)

    @property
    def retention_amount(self):
        """Retention value (percent or fixed) based on contract amount"""
        if self.retention_type == 'percent':
            return two_dec((self.retention_percent / Decimal('100')) * self.contract_amount)
        elif self.retention_type == 'amount':
            return two_dec(self.retention_fixed_amount)
        return two_dec(0)

    @property
    def cgst_amount(self):
        return two_dec((self.cgst_percent / Decimal('100')) * self.contract_amount)

    @property
    def sgst_amount(self):
        return two_dec((self.sgst_percent / Decimal('100')) * self.contract_amount)

    @property
    def total_tax_amount(self):
        """GST calculated on contract amount"""
        return two_dec((self.contract_amount * (self.cgst_percent + self.sgst_percent) / Decimal('100')))

    @property
    def certified_amount(self):
        """
        Net Amount = Contract Amount + GST - other_deductions - retention (if not released)
        """

        certified = self.contract_amount + self.total_tax_amount - self.other_deductions

        if not self.retention_released:
            certified -= self.retention_amount

        if certified < 0:
            certified = Decimal('0')

        return two_dec(certified)
    # models.py


    @property
    def certified_amount_display(self):
        """
        Certified amount for display & totals calculation.
        TDS deduction is always applied.
        Verification does NOT affect this value.
        """
        return self.value_of_work_done - (
            self.other_deductions +
            self.tds_amount
        )
    @property
    def retention_amount_display(self):
        return (self.retention_percent / 100) * self.contract_amount

    @property
    def total_tax_display(self):
        base = self.certified_amount_display
        return base * (self.cgst_percent + self.sgst_percent) / 100

    @property
    def total_received(self):
        """
        Total amount received = paid_amount - tds_amount
        """
        received = self.paid_amount - self.tds_amount
        return two_dec(received)

    # =====================================================
    # ================== SAVE OVERRIDE ====================
    # =====================================================

    def save(self, *args, **kwargs):

        # decimal safety
        self.contract_amount = two_dec(self.contract_amount)
        
        self.paid_amount = two_dec(self.paid_amount)
        self.tds_amount = two_dec(self.tds_amount)
        self.other_deductions = two_dec(self.other_deductions)

        # retention consistency
        if self.retention_type == 'percent':
            self.retention_fixed_amount = two_dec(0)
            self.retention_percent = two_dec(self.retention_percent)
        else:
            self.retention_percent = two_dec(0)
            self.retention_fixed_amount = two_dec(self.retention_fixed_amount)

        # auto retention release date
        if self.retention_released and not self.retention_released_date:
            self.retention_released_date = timezone.now().date()
        elif not self.retention_released:
            self.retention_released_date = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number}"


    

# =========================
# PAYMENT
# =========================
class Payment(models.Model):
    invoice = models.ForeignKey(
        'Invoice', on_delete=models.CASCADE, related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=4, default=0
    )
    payment_date = models.DateField()
    payment_mode = models.CharField(
        max_length=20,
        choices=[
            ('Cash', 'Cash'),
            ('Bank Transfer', 'Bank Transfer'),
            ('Cheque', 'Cheque'),
            ('Online', 'Online'),
        ],
        default='Bank Transfer'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def net_received(self):
        """
        If later you add TDS, you can subtract here.
        For now, full amount is received.
        """
        return self.amount

    def __str__(self):
        return f"Payment of ₹{self.amount} for {self.invoice.invoice_number}"

    class Meta:
        ordering = ['-payment_date', '-created_at']



# =========================
# COMPANY SETTINGS
# =========================
class CompanySettings(models.Model):
    company_name = models.CharField(max_length=200, default="")
    email = models.EmailField(default="")
    phone = models.CharField(max_length=20, default="")
    address = models.TextField(default="")

    invoice_prefix = models.CharField(max_length=20, default="INV")
    invoice_footer = models.TextField(
        default="Thank you for your business"
    )

    def __str__(self):
        return self.company_name
