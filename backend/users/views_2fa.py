from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import TwoFactorAuth, SecurityLog


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_2fa(request):
    """Setup 2FA for user"""
    try:
        # Get or create 2FA instance
        two_factor, created = TwoFactorAuth.objects.get_or_create(
            user=request.user,
            defaults={'secret_key': ''}
        )
        
        # Generate new secret
        secret = two_factor.generate_secret()
        qr_code = two_factor.generate_qr_code(request.user.email)
        
        # Generate backup codes
        backup_codes = two_factor.generate_backup_codes()
        
        return Response({
            'secret': secret,
            'qr_code': qr_code,
            'backup_codes': backup_codes,
            'instructions': 'Scan QR code with authenticator app or enter secret manually'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_2fa_setup(request):
    """Verify 2FA setup with token"""
    token = request.data.get('token')
    
    if not token:
        return Response({'error': 'Token required'}, status=400)
    
    try:
        two_factor = request.user.two_factor
        if two_factor.verify_token(token):
            two_factor.is_enabled = True
            two_factor.save()
            
            # Log security event
            SecurityLog.objects.create(
                user=request.user,
                event_type='2fa_enabled',
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'timestamp': timezone.now().isoformat()}
            )
            
            return Response({'message': '2FA enabled successfully'})
        else:
            return Response({'error': 'Invalid token'}, status=400)
            
    except TwoFactorAuth.DoesNotExist:
        return Response({'error': '2FA not setup'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_2fa_token(request):
    """Verify 2FA token for login"""
    token = request.data.get('token')
    backup_code = request.data.get('backup_code')
    
    try:
        two_factor = request.user.two_factor
        
        if not two_factor.is_enabled:
            return Response({'error': '2FA not enabled'}, status=400)
        
        # Check TOTP token first
        if token and two_factor.verify_token(token):
            two_factor.last_used = timezone.now()
            two_factor.save()
            return Response({'verified': True, 'method': 'totp'})
        
        # Check backup code
        elif backup_code and two_factor.verify_backup_code(backup_code):
            return Response({'verified': True, 'method': 'backup_code'})
        
        else:
            return Response({'error': 'Invalid token or backup code'}, status=400)
            
    except TwoFactorAuth.DoesNotExist:
        return Response({'error': '2FA not setup'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_2fa(request):
    """Disable 2FA for user"""
    password = request.data.get('password')
    token = request.data.get('token')
    
    if not password or not token:
        return Response({'error': 'Password and token required'}, status=400)
    
    # Verify password
    if not request.user.check_password(password):
        return Response({'error': 'Invalid password'}, status=400)
    
    try:
        two_factor = request.user.two_factor
        
        # Verify 2FA token
        if not two_factor.verify_token(token):
            return Response({'error': 'Invalid token'}, status=400)
        
        # Disable 2FA
        two_factor.is_enabled = False
        two_factor.secret_key = ''
        two_factor.backup_codes = []
        two_factor.save()
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='2fa_disabled',
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'timestamp': timezone.now().isoformat()}
        )
        
        return Response({'message': '2FA disabled successfully'})
        
    except TwoFactorAuth.DoesNotExist:
        return Response({'error': '2FA not setup'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_2fa_status(request):
    """Get 2FA status for user"""
    try:
        two_factor = request.user.two_factor
        return Response({
            'enabled': two_factor.is_enabled,
            'setup_complete': bool(two_factor.secret_key),
            'last_used': two_factor.last_used,
            'backup_codes_count': len(two_factor.backup_codes) if two_factor.backup_codes else 0
        })
    except TwoFactorAuth.DoesNotExist:
        return Response({
            'enabled': False,
            'setup_complete': False,
            'last_used': None,
            'backup_codes_count': 0
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_backup_codes(request):
    """Regenerate backup codes"""
    password = request.data.get('password')
    
    if not password:
        return Response({'error': 'Password required'}, status=400)
    
    # Verify password
    if not request.user.check_password(password):
        return Response({'error': 'Invalid password'}, status=400)
    
    try:
        two_factor = request.user.two_factor
        
        if not two_factor.is_enabled:
            return Response({'error': '2FA not enabled'}, status=400)
        
        # Generate new backup codes
        backup_codes = two_factor.generate_backup_codes()
        
        return Response({
            'backup_codes': backup_codes,
            'message': 'Backup codes regenerated successfully'
        })
        
    except TwoFactorAuth.DoesNotExist:
        return Response({'error': '2FA not setup'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
