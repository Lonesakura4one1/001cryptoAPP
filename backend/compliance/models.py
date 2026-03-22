from django.db import models
from django.conf import settings
from django.utils import timezone
import json


class KYCDocument(models.Model):
    """KYC document management"""
    DOCUMENT_TYPES = [
        ('passport', 'Passport'),
        ('driver_license', 'Driver License'),
        ('national_id', 'National ID'),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('selfie', 'Selfie with Document'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kyc_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # File storage
    front_image = models.ImageField(upload_to='kyc/front/')
    back_image = models.ImageField(upload_to='kyc/back/', null=True, blank=True)
    selfie_image = models.ImageField(upload_to='kyc/selfie/', null=True, blank=True)
    
    # Verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_score = models.IntegerField(default=0)  # 0-100 confidence score
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_kyc')
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Metadata
    extracted_data = models.JSONField(default=dict, blank=True)  # OCR extracted data
    verification_metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]


class KYCProfile(models.Model):
    """User KYC profile and verification level"""
    VERIFICATION_LEVELS = [
        (0, 'Not Verified'),
        (1, 'Basic - Email Verified'),
        (2, 'Tier 1 - Document Verified'),
        (3, 'Tier 2 - Enhanced Verification'),
        (4, 'Tier 3 - Institutional'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kyc_profile')
    verification_level = models.IntegerField(default=0, choices=VERIFICATION_LEVELS)
    
    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=50)
    country_of_residence = models.CharField(max_length=50)
    
    # Address
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    
    # Phone verification
    phone_number = models.CharField(max_length=20)
    phone_verified = models.BooleanField(default=False)
    
    # Risk assessment
    risk_score = models.IntegerField(default=0)  # 0-100 risk score
    risk_factors = models.JSONField(default=list, blank=True)
    
    # Limits based on verification level
    daily_transaction_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    monthly_transaction_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    annual_transaction_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Compliance flags
    is_politically_exposed = models.BooleanField(default=False)
    is_sanctioned = models.BooleanField(default=False)
    monitoring_required = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email} - Level {self.verification_level}"


class AMLTransaction(models.Model):
    """AML transaction monitoring"""
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    
    STATUS_CHOICES = [
        ('monitoring', 'Under Monitoring'),
        ('cleared', 'Cleared'),
        ('flagged', 'Flagged for Review'),
        ('reported', 'Reported to Authorities'),
        ('blocked', 'Transaction Blocked'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='aml_transactions')
    transaction_hash = models.CharField(max_length=100, unique=True)
    
    # Transaction details
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=10)
    from_address = models.CharField(max_length=100)
    to_address = models.CharField(max_length=100)
    
    # Risk assessment
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)
    risk_score = models.IntegerField(default=0)  # 0-100
    risk_factors = models.JSONField(default=list, blank=True)
    
    # AML checks
    sanction_check = models.BooleanField(default=False)
    pep_check = models.BooleanField(default=False)
    blacklist_check = models.BooleanField(default=False)
    unusual_pattern = models.BooleanField(default=False)
    
    # Review process
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='monitoring')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_aml')
    review_notes = models.TextField(blank=True, null=True)
    
    # Reporting
    sar_filed = models.BooleanField(default=False)  # Suspicious Activity Report
    sar_filed_date = models.DateTimeField(null=True, blank=True)
    ctr_filed = models.BooleanField(default=False)  # Currency Transaction Report
    ctr_filed_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'risk_level']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['risk_score']),
        ]


class ComplianceReport(models.Model):
    """Regulatory compliance reports"""
    REPORT_TYPES = [
        ('sar', 'Suspicious Activity Report'),
        ('ctr', 'Currency Transaction Report'),
        ('annual', 'Annual Compliance Report'),
        ('audit', 'Audit Report'),
        ('risk', 'Risk Assessment'),
    ]
    
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    report_id = models.CharField(max_length=100, unique=True)
    
    # Report details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Period
    report_period_start = models.DateField()
    report_period_end = models.DateField()
    
    # Content
    report_data = models.JSONField(default=dict)
    summary_statistics = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        default='draft'
    )
    
    # Submission
    submitted_to = models.CharField(max_length=100, blank=True, null=True)  # Regulatory body
    submitted_date = models.DateTimeField(null=True, blank=True)
    submission_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Review
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    review_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['report_period_start', 'report_period_end']),
        ]


class ComplianceRule(models.Model):
    """Automated compliance rules"""
    RULE_TYPES = [
        ('transaction_limit', 'Transaction Limit'),
        ('frequency_limit', 'Frequency Limit'),
        ('amount_threshold', 'Amount Threshold'),
        ('pattern_detection', 'Pattern Detection'),
        ('blacklist', 'Blacklist Check'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    
    # Rule configuration
    conditions = models.JSONField(default=dict)  # Rule conditions
    actions = models.JSONField(default=dict)     # Actions to take
    thresholds = models.JSONField(default=dict)  # Threshold values
    
    # Status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)  # Higher priority = executed first
    
    # Statistics
    trigger_count = models.IntegerField(default=0)
    last_triggered = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_rule_type_display()}"


class ComplianceAlert(models.Model):
    """Compliance alerts and notifications"""
    SEVERITY_LEVELS = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='compliance_alerts', null=True, blank=True)
    rule = models.ForeignKey(ComplianceRule, on_delete=models.SET_NULL, null=True, blank=True)
    
    alert_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related entities
    transaction_hash = models.CharField(max_length=100, blank=True, null=True)
    related_documents = models.JSONField(default=list, blank=True)
    
    # Status
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Resolution
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'severity']),
            models.Index(fields=['alert_type', 'created_at']),
            models.Index(fields=['is_acknowledged']),
        ]
