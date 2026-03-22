from rest_framework import serializers
from .models import Wallet, WalletAddress, ColdStorage, WalletBackup


class WalletSerializer(serializers.ModelSerializer):
    """Enhanced wallet serializer"""
    addresses = serializers.SerializerMethodField()
    balance = serializers.DecimalField(max_digits=20, decimal_places=8, read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'wallet_type', 'derivation_path', 'm_required', 'n_total',
            'public_keys', 'is_cold_storage', 'is_hardware_wallet',
            'last_backup', 'created_at', 'updated_at', 'addresses', 'balance'
        ]
        read_only_fields = ['created_at', 'updated_at', 'balance']
    
    def get_addresses(self, obj):
        addresses = WalletAddress.objects.filter(wallet=obj)
        return [
            {
                'address': addr.address,
                'address_type': addr.address_type,
                'derivation_path': addr.derivation_path,
                'is_used': addr.is_used,
                'created_at': addr.created_at
            }
            for addr in addresses
        ]


class WalletAddressSerializer(serializers.ModelSerializer):
    """Wallet address serializer"""
    class Meta:
        model = WalletAddress
        fields = [
            'id', 'address', 'address_type', 'derivation_path',
            'is_used', 'created_at'
        ]
        read_only_fields = ['created_at']


class HDWalletSetupSerializer(serializers.Serializer):
    """HD wallet setup serializer"""
    password = serializers.CharField(max_length=128, write_only=True)
    derivation_path = serializers.CharField(
        max_length=100,
        default="m/44'/0'/0'/0/0",
        required=False
    )
    
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters")
        return value


class MultiSigWalletSetupSerializer(serializers.Serializer):
    """Multi-signature wallet setup serializer"""
    m_required = serializers.IntegerField(min_value=1, max_value=15)
    n_total = serializers.IntegerField(min_value=1, max_value=15)
    public_keys = serializers.ListField(
        child=serializers.CharField(max_length=130),
        min_length=2,
        max_length=15
    )
    
    def validate(self, data):
        m = data['m_required']
        n = data['n_total']
        
        if m > n:
            raise serializers.ValidationError("Required signatures cannot exceed total keys")
        
        if len(data['public_keys']) != n:
            raise serializers.ValidationError("Public keys count must equal n_total")
        
        return data


class AddressGenerationSerializer(serializers.Serializer):
    """Address generation serializer"""
    password = serializers.CharField(max_length=128, write_only=True, required=False)
    address_type = serializers.ChoiceField(
        choices=['p2pkh', 'p2sh', 'bech32'],
        default='p2pkh'
    )


class WalletBackupSerializer(serializers.ModelSerializer):
    """Wallet backup serializer"""
    class Meta:
        model = WalletBackup
        fields = [
            'id', 'backup_type', 'location_info', 'created_at',
            'last_verified', 'is_secure'
        ]
        read_only_fields = ['created_at', 'last_verified', 'is_secure']


class ColdStorageSerializer(serializers.ModelSerializer):
    """Cold storage serializer"""
    class Meta:
        model = ColdStorage
        fields = [
            'id', 'storage_type', 'last_audit', 'next_audit',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ColdStorageSetupSerializer(serializers.Serializer):
    """Cold storage setup serializer"""
    storage_type = serializers.ChoiceField(
        choices=['paper', 'hardware', 'airgap']
    )
    password = serializers.CharField(max_length=128, write_only=True)
    location_info = serializers.JSONField(default=dict)


class WalletBackupSetupSerializer(serializers.Serializer):
    """Wallet backup setup serializer"""
    backup_type = serializers.ChoiceField(
        choices=['mnemonic', 'private_key', 'keystore', 'paper']
    )
    password = serializers.CharField(max_length=128, write_only=True)
