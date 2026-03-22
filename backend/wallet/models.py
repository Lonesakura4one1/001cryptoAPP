from django.db import models
from django.db.models import Q
from django.conf import settings
from decimal import Decimal
import json
from .crypto_utils import HDWallet, MultiSigWallet, CryptoUtils


class Wallet(models.Model):
    """Enhanced wallet model with HD and multisig support"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    
    wallet_type = models.CharField(
        max_length=20,
        choices=[
            ('hd', 'HD Wallet'),
            ('multisig', 'Multi-Signature'),
            ('simple', 'Simple Address'),
        ],
        default='hd'
    )
    
    # HD Wallet fields
    mnemonic_encrypted = models.TextField(blank=True, null=True)
    seed_encrypted = models.TextField(blank=True, null=True)
    derivation_path = models.CharField(max_length=100, default="m/44'/0'/0'/0/0")
    
    # Multi-sig fields
    m_required = models.IntegerField(default=1)  # Required signatures
    n_total = models.IntegerField(default=1)    # Total keys
    public_keys = models.JSONField(default=list, blank=True)
    redeem_script = models.TextField(blank=True, null=True)
    
    # Security
    is_cold_storage = models.BooleanField(default=False)
    is_hardware_wallet = models.BooleanField(default=False)
    last_backup = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_wallet_type_display()}"

    @property
    def balance(self) -> Decimal:
        """
        Ledger-based balance (derived, never stored)
        """
        deposits = self.transactions.filter(
            transaction_type=Transaction.DEPOSIT,
            is_active=True
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

        withdrawals = self.transactions.filter(
            transaction_type=Transaction.WITHDRAW,
            is_active=True
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

        return deposits - withdrawals
    
    def get_hd_wallet(self, password=None):
        """Get HD wallet instance"""
        if self.wallet_type != 'hd':
            return None
        
        if self.seed_encrypted and password:
            encrypted_data = {
                'encrypted_key': self.seed_encrypted,
                'salt': json.loads(getattr(self, 'seed_salt', '""'))
            }
            seed = CryptoUtils.decrypt_private_key(encrypted_data, password)
            return HDWallet(seed)
        
        return HDWallet()
    
    def get_multisig_wallet(self):
        """Get multi-sig wallet instance"""
        if self.wallet_type != 'multisig':
            return None
        
        multisig = MultiSigWallet(self.m_required, self.n_total)
        for pubkey in self.public_keys:
            multisig.add_public_key(bytes.fromhex(pubkey))
        
        return multisig
    
    def generate_address(self, password=None, address_type='p2pkh'):
        """Generate new address"""
        if self.wallet_type == 'hd':
            hd_wallet = self.get_hd_wallet(password)
            if hd_wallet:
                # Derive key from path
                key = hd_wallet.derive_path(self.derivation_path)
                return hd_wallet.get_address(key['private_key'], address_type)
        
        elif self.wallet_type == 'multisig':
            multisig = self.get_multisig_wallet()
            if multisig:
                return multisig.get_address()
        
        return None
    
    def setup_hd_wallet(self, password=None):
        """Setup HD wallet with new mnemonic"""
        if self.wallet_type != 'hd':
            return False
        
        # Generate new HD wallet
        hd_wallet = HDWallet()
        mnemonic = CryptoUtils.generate_mnemonic()
        seed = CryptoUtils.mnemonic_to_seed(mnemonic)
        
        if password:
            # Encrypt seed
            encrypted_data = CryptoUtils.encrypt_private_key(seed, password)
            self.seed_encrypted = encrypted_data['encrypted_key']
            self.seed_salt = json.dumps(encrypted_data['salt'])
        else:
            self.seed_encrypted = None
        
        self.mnemonic_encrypted = mnemonic  # In production, encrypt this too
        self.save()
        
        return True
    
    def setup_multisig_wallet(self, m_required, n_total, public_keys):
        """Setup multi-signature wallet"""
        self.wallet_type = 'multisig'
        self.m_required = m_required
        self.n_total = n_total
        self.public_keys = public_keys
        
        # Generate redeem script
        multisig = MultiSigWallet(m_required, n_total)
        for pubkey in public_keys:
            multisig.add_public_key(bytes.fromhex(pubkey))
        
        self.redeem_script = multisig.generate_redeem_script().hex()
        self.save()
        
        return True


class WalletAddress(models.Model):
    """Track generated addresses for wallets"""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='addresses')
    address = models.CharField(max_length=100)
    address_type = models.CharField(max_length=20, default='p2pkh')
    derivation_path = models.CharField(max_length=100, blank=True, null=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['wallet', 'address']
        indexes = [
            models.Index(fields=['wallet', 'is_used']),
        ]


class Transaction(models.Model):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"

    TRANSACTION_TYPES = (
        (DEPOSIT, "Deposit"),
        (WITHDRAW, "Withdraw"),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True
    )

    amount = models.DecimalField(max_digits=20, decimal_places=8)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    
    # Enhanced transaction fields
    tx_hash = models.CharField(max_length=100, blank=True, null=True)
    from_address = models.CharField(max_length=100, blank=True, null=True)
    to_address = models.CharField(max_length=100, blank=True, null=True)
    confirmations = models.IntegerField(default=0)
    block_height = models.IntegerField(null=True, blank=True)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.amount}"


class ColdStorage(models.Model):
    """Cold storage wallet management"""
    wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE, related_name='cold_storage')
    
    storage_type = models.CharField(
        max_length=20,
        choices=[
            ('paper', 'Paper Wallet'),
            ('hardware', 'Hardware Wallet'),
            ('airgap', 'Air-gapped Computer'),
        ]
    )
    
    location_encrypted = models.TextField(blank=True, null=True)  # Encrypted location info
    access_controls = models.JSONField(default=dict, blank=True)  # Multi-person access requirements
    
    last_audit = models.DateTimeField(null=True, blank=True)
    next_audit = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WalletBackup(models.Model):
    """Wallet backup records"""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='backups')
    
    backup_type = models.CharField(
        max_length=20,
        choices=[
            ('mnemonic', 'Mnemonic Phrase'),
            ('private_key', 'Private Key'),
            ('keystore', 'Keystore File'),
            ('paper', 'Paper Backup'),
        ]
    )
    
    backup_data_encrypted = models.TextField()
    location_info = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    is_secure = models.BooleanField(default=True)
