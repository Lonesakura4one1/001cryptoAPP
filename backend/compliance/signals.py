from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import KYCProfile, AMLTransaction, ComplianceAlert
from .services import AMLService, ComplianceEngine
from backend.wallet.models import Transaction
from backend.users.models import SecurityLog


@receiver(post_save, sender=KYCProfile)
def kyc_profile_created(sender, instance, created, **kwargs):
    """Handle KYC profile creation"""
    if created:
        # Log security event
        SecurityLog.objects.create(
            user=instance.user,
            event_type='kyc_submitted',
            details={
                'verification_level': instance.verification_level,
                'timestamp': instance.created_at.isoformat()
            }
        )


@receiver(pre_save, sender=Transaction)
def transaction_pre_save(sender, instance, **kwargs):
    """Run compliance checks before saving transaction"""
    if instance.user and not instance.pk:  # Only for new transactions
        # Run compliance evaluation
        transaction_data = {
            'amount': instance.amount,
            'to_address': instance.to_address or '',
            'from_address': instance.from_address or '',
            'currency': 'BTC',  # Default, should be dynamic
        }
        
        result = ComplianceEngine.evaluate_transaction(instance.user, transaction_data)
        
        if not result['approved']:
            # Block transaction
            instance.status = 'failed'
            instance.is_active = False
        else:
            instance.status = 'pending'


@receiver(post_save, sender=Transaction)
def transaction_post_save(sender, instance, created, **kwargs):
    """Handle transaction creation for AML monitoring"""
    if created and instance.user:
        # Run AML analysis
        transaction_data = {
            'amount': instance.amount,
            'to_address': instance.to_address or '',
            'from_address': instance.from_address or '',
            'currency': 'BTC',
            'tx_hash': instance.tx_hash or '',
        }
        
        aml_analysis = AMLService.analyze_transaction(instance.user, transaction_data)
        
        # Create AML record for high-risk transactions
        if aml_analysis['risk_score'] >= 30:
            AMLService.create_aml_record(instance.user, transaction_data, aml_analysis)
        
        # Create compliance alerts for critical risks
        if aml_analysis['risk_level'] == 'critical':
            ComplianceAlert.objects.create(
                user=instance.user,
                alert_type='critical_aml_risk',
                severity='critical',
                title='Critical AML Risk Detected',
                message=f"Transaction {instance.tx_hash} flagged with critical AML risk score: {aml_analysis['risk_score']}",
                transaction_hash=instance.tx_hash,
            )


@receiver(post_save, sender=AMLTransaction)
def aml_transaction_created(sender, instance, created, **kwargs):
    """Handle AML transaction creation"""
    if created and instance.risk_level in ['high', 'critical']:
        # Create compliance alert for high-risk transactions
        ComplianceAlert.objects.create(
            user=instance.user,
            alert_type='aml_review_required',
            severity='error' if instance.risk_level == 'critical' else 'warning',
            title='AML Review Required',
            message=f"Transaction {instance.transaction_hash} requires AML review. Risk level: {instance.risk_level}",
            transaction_hash=instance.transaction_hash,
        )
