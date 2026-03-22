from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Wallet, WalletAddress, ColdStorage, WalletBackup
from .crypto_utils import HDWallet, MultiSigWallet, CryptoUtils


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_hd_wallet(request):
    """Setup HD wallet for user"""
    try:
        data = request.data
        password = data.get('password')
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(
            user=request.user,
            defaults={'wallet_type': 'hd'}
        )
        
        if wallet.wallet_type != 'hd':
            return Response({'error': 'Wallet type mismatch'}, status=400)
        
        # Setup HD wallet
        if wallet.setup_hd_wallet(password):
            return Response({
                'message': 'HD wallet created successfully',
                'wallet_type': wallet.wallet_type,
                'derivation_path': wallet.derivation_path
            })
        else:
            return Response({'error': 'Failed to setup HD wallet'}, status=400)
            
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_multisig_wallet(request):
    """Setup multi-signature wallet"""
    try:
        data = request.data
        m_required = data.get('m_required')
        n_total = data.get('n_total')
        public_keys = data.get('public_keys', [])
        
        if not all([m_required, n_total, public_keys]):
            return Response({'error': 'Missing required fields'}, status=400)
        
        if len(public_keys) != n_total:
            return Response({'error': 'Public keys count mismatch'}, status=400)
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(
            user=request.user,
            defaults={'wallet_type': 'multisig'}
        )
        
        if wallet.setup_multisig_wallet(m_required, n_total, public_keys):
            return Response({
                'message': 'Multi-sig wallet created successfully',
                'm_required': m_required,
                'n_total': n_total,
                'address': wallet.get_address()
            })
        else:
            return Response({'error': 'Failed to setup multi-sig wallet'}, status=400)
            
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_address(request):
    """Generate new address for wallet"""
    try:
        data = request.data
        password = data.get('password')
        address_type = data.get('address_type', 'p2pkh')
        
        wallet = request.user.wallet
        
        if not wallet:
            return Response({'error': 'No wallet found'}, status=404)
        
        address = wallet.generate_address(password, address_type)
        
        if not address:
            return Response({'error': 'Failed to generate address'}, status=400)
        
        # Save address
        WalletAddress.objects.create(
            wallet=wallet,
            address=address,
            address_type=address_type,
            derivation_path=wallet.derivation_path if wallet.wallet_type == 'hd' else None
        )
        
        return Response({
            'address': address,
            'address_type': address_type,
            'derivation_path': wallet.derivation_path
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_addresses(request):
    """Get all wallet addresses"""
    try:
        wallet = request.user.wallet
        
        if not wallet:
            return Response({'error': 'No wallet found'}, status=404)
        
        addresses = WalletAddress.objects.filter(wallet=wallet)
        
        return Response({
            'addresses': [
                {
                    'address': addr.address,
                    'address_type': addr.address_type,
                    'derivation_path': addr.derivation_path,
                    'is_used': addr.is_used,
                    'created_at': addr.created_at
                }
                for addr in addresses
            ]
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_wallet(request):
    """Create wallet backup"""
    try:
        data = request.data
        password = data.get('password')
        backup_type = data.get('backup_type', 'mnemonic')
        
        wallet = request.user.wallet
        
        if not wallet:
            return Response({'error': 'No wallet found'}, status=404)
        
        backup_data = {}
        
        if wallet.wallet_type == 'hd':
            if not password:
                return Response({'error': 'Password required for HD wallet backup'}, status=400)
            
            hd_wallet = wallet.get_hd_wallet(password)
            if hd_wallet:
                backup_data = {
                    'mnemonic': wallet.mnemonic_encrypted,
                    'seed_encrypted': wallet.seed_encrypted
                }
        
        # Create backup record
        backup = WalletBackup.objects.create(
            wallet=wallet,
            backup_type=backup_type,
            backup_data_encrypted=CryptoUtils.encrypt_private_key(
                str(backup_data).encode(), password
            )['encrypted_key']
        )
        
        return Response({
            'message': 'Backup created successfully',
            'backup_id': backup.id,
            'backup_type': backup_type
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_cold_storage(request):
    """Setup cold storage for wallet"""
    try:
        data = request.data
        storage_type = data.get('storage_type')
        location_info = data.get('location_info', {})
        
        wallet = request.user.wallet
        
        if not wallet:
            return Response({'error': 'No wallet found'}, status=404)
        
        # Mark wallet as cold storage
        wallet.is_cold_storage = True
        wallet.save()
        
        # Create cold storage record
        cold_storage = ColdStorage.objects.create(
            wallet=wallet,
            storage_type=storage_type,
            location_encrypted=CryptoUtils.encrypt_private_key(
                str(location_info).encode(), data.get('password', '')
            )['encrypted_key']
        )
        
        return Response({
            'message': 'Cold storage setup successfully',
            'storage_type': storage_type,
            'next_audit': cold_storage.next_audit
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)
