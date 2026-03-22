"""
Background tasks for crypto platform.
"""

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from django.db import models
from datetime import timedelta
from backend.transactions.api_clients import get_exchange_client
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_crypto_prices():
    """
    Update cryptocurrency prices from external APIs.
    """
    try:
        exchange = get_exchange_client('coingecko')
        
        # Get supported currencies from settings
        from django.conf import settings
        currencies = settings.CRYPTO_PLATFORM['SUPPORTED_CURRENCIES']
        
        updated_prices = {}
        
        for currency in currencies:
            try:
                price = exchange.get_price(currency)
                updated_prices[currency] = price
                logger.info(f"Updated {currency} price: ${price}")
            except Exception as e:
                logger.error(f"Failed to update {currency} price: {str(e)}")
        
        # Cache the prices
        from django.core.cache import cache
        cache.set('crypto_prices', updated_prices, timeout=300)  # 5 minutes
        
        return {
            'status': 'success',
            'updated_count': len(updated_prices),
            'prices': {k: str(v) for k, v in updated_prices.items()}
        }
        
    except Exception as e:
        logger.error(f"Price update failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task
def process_aml_checks():
    """
    Process AML checks for pending transactions.
    """
    try:
        from .compliance.models import AMLTransaction, ComplianceRule
        from .compliance.services import AMLService
        
        # Get pending AML transactions
        pending_transactions = AMLTransaction.objects.filter(
            status='monitoring'
        ).select_related('user')
        
        processed_count = 0
        alerts_count = 0
        
        for transaction in pending_transactions:
            try:
                aml_service = AMLService()
                result = aml_service.analyze_transaction(transaction)
                
                if result['risk_level'] in ['high', 'critical']:
                    alerts_count += 1
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"AML check failed for transaction {transaction.transaction_hash}: {str(e)}")
        
        logger.info(f"Processed {processed_count} AML checks, generated {alerts_count} alerts")
        
        return {
            'status': 'success',
            'processed_count': processed_count,
            'alerts_count': alerts_count
        }
        
    except Exception as e:
        logger.error(f"AML processing failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task
def cleanup_expired_sessions():
    """
    Clean up expired user sessions.
    """
    try:
        from .users.models import UserSession
        
        # Delete sessions older than 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        deleted_count = UserSession.objects.filter(
            created_at__lt=cutoff_time,
            is_active=False
        ).delete()[0]
        
        # Deactivate sessions older than 1 hour
        cutoff_time = timezone.now() - timedelta(hours=1)
        deactivated_count = UserSession.objects.filter(
            last_activity__lt=cutoff_time,
            is_active=True
        ).update(is_active=False)
        
        logger.info(f"Cleaned up {deleted_count} expired sessions, deactivated {deactivated_count} inactive sessions")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'deactivated_count': deactivated_count
        }
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task
def generate_daily_reports():
    """
    Generate daily compliance and trading reports.
    """
    try:
        from .compliance.models import ComplianceReport
        from .trading.models import Trade, Order
        from datetime import date
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Trading volume report
        trades_yesterday = Trade.objects.filter(
            created_at__date=yesterday
        ).aggregate(
            total_volume=models.Sum('size'),
            total_trades=models.Count('id'),
            total_fees=models.Sum(models.F('taker_fee') + models.F('maker_fee'))
        )
        
        # Order statistics
        orders_yesterday = Order.objects.filter(
            created_at__date=yesterday
        ).aggregate(
            total_orders=models.Count('id'),
            filled_orders=models.Count('id', filter=models.Q(status='filled'))
        )
        
        # Create compliance report
        report_data = {
            'trading': {
                'date': yesterday.isoformat(),
                'total_volume': str(trades_yesterday['total_volume'] or 0),
                'total_trades': trades_yesterday['total_trades'] or 0,
                'total_fees': str(trades_yesterday['total_fees'] or 0),
                'total_orders': orders_yesterday['total_orders'] or 0,
                'filled_orders': orders_yesterday['filled_orders'] or 0,
                'fill_rate': (
                    (orders_yesterday['filled_orders'] or 0) / max(orders_yesterday['total_orders'] or 1, 1)
                ) * 100
            }
        }
        
        report = ComplianceReport.objects.create(
            report_type='daily',
            report_id=f'daily-{yesterday.isoformat()}',
            title=f'Daily Trading Report - {yesterday}',
            report_period_start=yesterday,
            report_period_end=yesterday,
            report_data=report_data,
            summary_statistics={
                'total_volume': float(trades_yesterday['total_volume'] or 0),
                'total_trades': trades_yesterday['total_trades'] or 0,
                'total_orders': orders_yesterday['total_orders'] or 0
            }
        )
        
        logger.info(f"Generated daily report {report.report_id}")
        
        return {
            'status': 'success',
            'report_id': report.report_id,
            'date': yesterday.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Daily report generation failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task
def send_email_notification(user_id, subject, message, template=None):
    """
    Send email notification to user.
    """
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.conf import settings
        
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@cryptoplatform.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Email sent to user {user.email}")
        
        return {
            'status': 'success',
            'user_email': user.email
        }
        
    except Exception as e:
        logger.error(f"Failed to send email to user {user_id}: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task
def backup_wallet_data(wallet_id):
    """
    Create backup of wallet data.
    """
    try:
        from .wallet.models import Wallet, WalletBackup
        from .wallet.crypto_utils import CryptoUtils
        import json
        
        wallet = Wallet.objects.get(id=wallet_id)
        
        # Create backup data
        backup_data = {
            'wallet_type': wallet.wallet_type,
            'created_at': wallet.created_at.isoformat(),
            'addresses': [
                {
                    'address': addr.address,
                    'type': addr.address_type,
                    'created_at': addr.created_at.isoformat()
                }
                for addr in wallet.addresses.all()
            ]
        }
        
        # Add sensitive data for HD wallets
        if wallet.wallet_type == 'hd' and wallet.mnemonic_encrypted:
            backup_data['mnemonic_encrypted'] = wallet.mnemonic_encrypted
            backup_data['derivation_path'] = wallet.derivation_path
        
        # Encrypt backup data
        backup_json = json.dumps(backup_data)
        encrypted_backup = CryptoUtils.encrypt_private_key(
            backup_json.encode(),
            'default-backup-key'  # In production, use a proper key management system
        )
        
        # Create backup record
        backup = WalletBackup.objects.create(
            wallet=wallet,
            backup_type='encrypted',
            backup_data_encrypted=encrypted_backup['encrypted_key'],
            location_info={'method': 'automated_daily'}
        )
        
        logger.info(f"Created backup for wallet {wallet_id}")
        
        return {
            'status': 'success',
            'backup_id': backup.id,
            'wallet_id': wallet_id
        }
        
    except Exception as e:
        logger.error(f"Wallet backup failed for wallet {wallet_id}: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }
