from django.db import models
from django.contrib.auth.models import AbstractUser
import pyotp
import qrcode
from io import BytesIO
import base64


class User(AbstractUser):
    """Extended user model with 2FA support"""
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    kyc_level = models.IntegerField(default=0)  # 0=none, 1=basic, 2=advanced
    risk_score = models.IntegerField(default=0)  # 0=low, 100=high risk
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class TwoFactorAuth(models.Model):
    """TOTP 2FA configuration for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    secret_key = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    def generate_secret(self):
        """Generate new TOTP secret"""
        self.secret_key = pyotp.random_base32()
        self.save()
        return self.secret_key
    
    def get_otp_uri(self, user_email):
        """Generate OTP URI for QR code"""
        return pyotp.totp.TOTP(self.secret_key).provisioning_uri(
            name=user_email,
            issuer_name="Crypto Platform"
        )
    
    def generate_qr_code(self, user_email):
        """Generate QR code for TOTP setup"""
        otp_uri = self.get_otp_uri(user_email)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(otp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code}"
    
    def verify_token(self, token):
        """Verify TOTP token"""
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self):
        """Generate backup codes"""
        codes = [pyotp.random_base32()[:8] for _ in range(10)]
        self.backup_codes = codes
        self.save()
        return codes
    
    def verify_backup_code(self, code):
        """Verify and consume backup code"""
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save()
            return True
        return False

class UserSession(models.Model):
    """Track user sessions for security"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]

class SecurityLog(models.Model):
    """Log security events"""
    EVENT_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
        ('password_changed', 'Password Changed'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('kyc_submitted', 'KYC Submitted'),
        ('kyc_approved', 'KYC Approved'),
        ('kyc_rejected', 'KYC Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_logs')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]
