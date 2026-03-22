from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from backend.wallet.models import Wallet, Transaction
from backend.wallet.crypto_utils import HDWallet, CryptoUtils

User = get_user_model()

class WalletModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Use get_or_create to avoid unique constraint issues
        self.wallet, created = Wallet.objects.get_or_create(
            user=self.user,
            defaults={'wallet_type': 'hd'}
        )
    
    def test_wallet_creation(self):
        self.assertEqual(self.wallet.user, self.user)
        self.assertEqual(self.wallet.wallet_type, 'hd')
        self.assertEqual(str(self.wallet), f"{self.user.username} - HD Wallet")
    
    def test_hd_wallet_setup(self):
        result = self.wallet.setup_hd_wallet('testpassword123')
        self.assertTrue(result)
        self.assertIsNotNone(self.wallet.mnemonic_encrypted)
    
    def test_address_generation(self):
        self.wallet.setup_hd_wallet('testpassword123')
        address = self.wallet.generate_address('testpassword123')
        self.assertIsNotNone(address)
        self.assertTrue(len(address) > 20)  # Basic address length check
    
    def test_transaction_balance_calculation(self):
        # Create test transactions
        Transaction.objects.create(
            user=self.user,
            wallet=self.wallet,
            amount=Decimal('100.0'),
            transaction_type=Transaction.DEPOSIT
        )
        Transaction.objects.create(
            user=self.user,
            wallet=self.wallet,
            amount=Decimal('30.0'),
            transaction_type=Transaction.WITHDRAW
        )
        
        balance = self.wallet.balance
        self.assertEqual(balance, Decimal('70.0'))


class CryptoUtilsTest(TestCase):
    def test_mnemonic_generation(self):
        mnemonic = CryptoUtils.generate_mnemonic()
        self.assertTrue(len(mnemonic.split()) == 12 or len(mnemonic.split()) == 24)
        self.assertTrue(CryptoUtils.verify_mnemonic(mnemonic))
    
    def test_mnemonic_to_seed(self):
        mnemonic = CryptoUtils.generate_mnemonic()
        seed = CryptoUtils.mnemonic_to_seed(mnemonic)
        self.assertIsInstance(seed, bytes)
        self.assertEqual(len(seed), 64)  # BIP39 seed length
    
    def test_hd_wallet_creation(self):
        hd_wallet = HDWallet()
        self.assertIsNotNone(hd_wallet.seed)
        self.assertIsNotNone(hd_wallet.master_key)
    
    def test_address_derivation(self):
        hd_wallet = HDWallet()
        key = hd_wallet.derive_path("m/44'/0'/0'/0/0")
        self.assertIsNotNone(key)
        self.assertIn('private_key', key)
        self.assertIn('chain_code', key)
