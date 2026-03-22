from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum
from .models import KYCProfile, AMLTransaction, ComplianceRule, ComplianceAlert
from backend.wallet.models import Transaction


class KYCService:
    """KYC verification and management service"""
    
    @staticmethod
    def create_kyc_profile(user, profile_data):
        """Create KYC profile for user"""
        profile = KYCProfile.objects.create(
            user=user,
            **profile_data
        )
        
        # Set initial limits based on verification level
        KYCService.update_transaction_limits(profile)
        
        return profile
    
    @staticmethod
    def update_verification_level(user, new_level):
        """Update user verification level and limits"""
        try:
            profile = user.kyc_profile
            old_level = profile.verification_level
            profile.verification_level = new_level
            profile.save()
            
            # Update transaction limits
            KYCService.update_transaction_limits(profile)
            
            # Log security event
            from users.models import SecurityLog
            SecurityLog.objects.create(
                user=user,
                event_type='kyc_approved' if new_level > old_level else 'kyc_rejected',
                details={
                    'old_level': old_level,
                    'new_level': new_level,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            return True
        except KYCProfile.DoesNotExist:
            return False
    
    @staticmethod
    def update_transaction_limits(profile):
        """Update transaction limits based on verification level"""
        limits = {
            0: {'daily': 0, 'monthly': 0, 'annual': 0},
            1: {'daily': Decimal('100'), 'monthly': Decimal('1000'), 'annual': Decimal('10000')},
            2: {'daily': Decimal('1000'), 'monthly': Decimal('10000'), 'annual': Decimal('100000')},
            3: {'daily': Decimal('10000'), 'monthly': Decimal('100000'), 'annual': Decimal('1000000')},
            4: {'daily': Decimal('100000'), 'monthly': Decimal('1000000'), 'annual': Decimal('10000000')},
        }
        
        level_limits = limits.get(profile.verification_level, limits[0])
        profile.daily_transaction_limit = level_limits['daily']
        profile.monthly_transaction_limit = level_limits['monthly']
        profile.annual_transaction_limit = level_limits['annual']
        profile.save()
    
    @staticmethod
    def check_transaction_limits(user, amount):
        """Check if transaction exceeds user limits"""
        try:
            profile = user.kyc_profile
            
            # Get current transaction totals
            today = timezone.now().date()
            current_month = today.replace(day=1)
            current_year = today.replace(month=1, day=1)
            
            daily_total = Transaction.objects.filter(
                user=user,
                created_at__date=today,
                status='confirmed'
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
            
            monthly_total = Transaction.objects.filter(
                user=user,
                created_at__date__gte=current_month,
                status='confirmed'
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
            
            annual_total = Transaction.objects.filter(
                user=user,
                created_at__date__gte=current_year,
                status='confirmed'
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
            
            # Check limits
            limits = {
                'daily': (daily_total + amount) <= profile.daily_transaction_limit,
                'monthly': (monthly_total + amount) <= profile.monthly_transaction_limit,
                'annual': (annual_total + amount) <= profile.annual_transaction_limit,
            }
            
            return limits, {
                'daily_current': daily_total,
                'monthly_current': monthly_total,
                'annual_current': annual_total,
                'daily_limit': profile.daily_transaction_limit,
                'monthly_limit': profile.monthly_transaction_limit,
                'annual_limit': profile.annual_transaction_limit,
            }
            
        except KYCProfile.DoesNotExist:
            return {'daily': False, 'monthly': False, 'annual': False}, {}


class AMLService:
    """AML transaction monitoring service"""
    
    @staticmethod
    def analyze_transaction(user, transaction_data):
        """Analyze transaction for AML risks"""
        from wallet.models import Transaction
        from django.db.models import Sum
        
        amount = transaction_data.get('amount', 0)
        to_address = transaction_data.get('to_address', '')
        
        # Calculate risk score
        risk_score = 0
        risk_factors = []
        
        # Amount-based risk factors
        if amount >= 10000:
            risk_score += 30
            risk_factors.append('high_amount')
        elif amount >= 1000:
            risk_score += 15
            risk_factors.append('medium_amount')
        
        # Frequency-based risk factors
        recent_transactions = Transaction.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        
        if recent_transactions > 10:
            risk_score += 25
            risk_factors.append('high_frequency')
        elif recent_transactions > 5:
            risk_score += 10
            risk_factors.append('medium_frequency')
        
        # Pattern detection
        total_24h = Transaction.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timezone.timedelta(hours=24),
            status='confirmed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        if total_24h >= 25000:
            risk_score += 20
            risk_factors.append('structuring_pattern')
        
        # Address-based checks (simplified)
        if AMLService.is_high_risk_address(to_address):
            risk_score += 40
            risk_factors.append('high_risk_address')
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = 'critical'
        elif risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'requires_review': risk_score >= 50
        }
    
    @staticmethod
    def is_high_risk_address(address):
        """Check if address is on any blacklist"""
        # Simplified check - in production, integrate with real blacklist APIs
        blacklisted_patterns = [
            'mixing', 'tumbler', 'gambling', 'darknet'
        ]
        return any(pattern in address.lower() for pattern in blacklisted_patterns)
    
    @staticmethod
    def create_aml_record(user, transaction_data, analysis_result):
        """Create AML monitoring record"""
        return AMLTransaction.objects.create(
            user=user,
            transaction_hash=transaction_data.get('tx_hash', ''),
            amount=transaction_data.get('amount', 0),
            currency=transaction_data.get('currency', 'BTC'),
            from_address=transaction_data.get('from_address', ''),
            to_address=transaction_data.get('to_address', ''),
            risk_level=analysis_result['risk_level'],
            risk_score=analysis_result['risk_score'],
            risk_factors=analysis_result['risk_factors'],
            sanction_check=AMLService.check_sanctions(user),
            pep_check=AMLService.check_pep(user),
            blacklist_check=AMLService.is_high_risk_address(transaction_data.get('to_address', '')),
            unusual_pattern='structuring_pattern' in analysis_result['risk_factors']
        )
    
    @staticmethod
    def check_sanctions(user):
        """Check if user is on sanctions list"""
        # Simplified check - in production, integrate with real sanctions APIs
        try:
            profile = user.kyc_profile
            return profile.is_sanctioned
        except KYCProfile.DoesNotExist:
            return False
    
    @staticmethod
    def check_pep(user):
        """Check if user is politically exposed person"""
        # Simplified check - in production, integrate with real PEP databases
        try:
            profile = user.kyc_profile
            return profile.is_politically_exposed
        except KYCProfile.DoesNotExist:
            return False


class ComplianceEngine:
    """Main compliance engine that orchestrates all compliance checks"""
    
    @staticmethod
    def evaluate_transaction(user, transaction_data):
        """Evaluate transaction against all compliance rules"""
        results = {
            'kyc_check': None,
            'aml_check': None,
            'limit_check': None,
            'approved': False,
            'reasons': []
        }
        
        # KYC check
        kyc_limits, limit_details = KYCService.check_transaction_limits(
            user, transaction_data.get('amount', 0)
        )
        results['limit_check'] = {
            'passed': all(kyc_limits.values()),
            'details': limit_details
        }
        
        if not all(kyc_limits.values()):
            results['reasons'].append('Transaction limits exceeded')
        
        # AML check
        aml_analysis = AMLService.analyze_transaction(user, transaction_data)
        results['aml_check'] = aml_analysis
        
        if aml_analysis['requires_review']:
            results['reasons'].append('High AML risk detected')
        
        # Create AML record if needed
        if aml_analysis['risk_score'] >= 30:
            AMLService.create_aml_record(user, transaction_data, aml_analysis)
        
        # Final decision
        results['approved'] = (
            all(kyc_limits.values()) and 
            not aml_analysis['requires_review']
        )
        
        # Create compliance alert if needed
        if not results['approved']:
            ComplianceAlert.objects.create(
                user=user,
                alert_type='transaction_blocked',
                severity='error' if aml_analysis['risk_level'] == 'critical' else 'warning',
                title='Transaction Compliance Check Failed',
                message=f"Transaction blocked: {', '.join(results['reasons'])}",
                transaction_hash=transaction_data.get('tx_hash'),
            )
        
        return results
