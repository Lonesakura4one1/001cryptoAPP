from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import json
from backend.trading.models import TradingPair

User = get_user_model()

class AuthenticationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'username': 'testuser'
        }
    
    def test_user_registration(self):
        response = self.client.post('/api/users/register/', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
    
    def test_user_login(self):
        # Create user first
        User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/auth/login/', login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class WalletAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_wallet_detail(self):
        response = self.client.get('/api/wallet/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('balance', response.data)
    
    def test_deposit_transaction(self):
        data = {
            'amount': '100.00',
            'idempotency_key': 'test-deposit-123'
        }
        
        response = self.client.post('/api/wallet/deposit/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
    
    def test_withdraw_transaction(self):
        data = {
            'amount': '50.00',
            'idempotency_key': 'test-withdraw-123'
        }
        
        response = self.client.post('/api/wallet/withdraw/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
    
    def test_transaction_history(self):
        response = self.client.get('/api/wallet/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('transactions', response.data)


class TradingAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='trader@example.com',
            password='testpass123',
            username='trader'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create trading pair
        self.trading_pair = TradingPair.objects.create(
            base_currency='BTC',
            quote_currency='USD',
            symbol='BTC-USD',
            min_order_size=Decimal('0.001'),
            max_order_size=Decimal('100')
        )
    
    def test_get_trading_pairs(self):
        response = self.client.get('/api/trading/pairs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_place_order(self):
        data = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'size': '1.0',
            'order_type': 'limit',
            'price': '50000.00'
        }
        
        response = self.client.post('/api/trading/orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('order', response.data)
    
    def test_get_orders(self):
        response = self.client.get('/api/trading/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('orders', response.data)
    
    def test_get_trades(self):
        response = self.client.get('/api/trading/trades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('trades', response.data)
    
    def test_get_order_book(self):
        response = self.client.get('/api/trading/orderbook/BTC-USD/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bids', response.data)
        self.assertIn('asks', response.data)


class ComplianceAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            username='user'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_submit_kyc_profile(self):
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        }
        
        response = self.client.post('/api/compliance/kyc/profile/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
    
    def test_get_kyc_status(self):
        response = self.client.get('/api/compliance/kyc/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('verification_level', response.data)
    
    def test_get_compliance_alerts(self):
        response = self.client.get('/api/compliance/alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class TwoFactorAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            username='user'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_setup_2fa(self):
        response = self.client.post('/api/users/2fa/setup/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret', response.data)
        self.assertIn('qr_code', response.data)
        self.assertIn('backup_codes', response.data)
    
    def test_get_2fa_status(self):
        response = self.client.get('/api/users/2fa/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('enabled', response.data)
        self.assertIn('setup_complete', response.data)


class IntegrationTest(TestCase):
    """Integration tests for complete workflows"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='trader@example.com',
            password='testpass123',
            username='trader'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_complete_trading_workflow(self):
        """Test complete trading workflow from registration to trade execution"""
        
        # 1. Setup 2FA
        setup_response = self.client.post('/api/users/2fa/setup/', format='json')
        self.assertEqual(setup_response.status_code, status.HTTP_200_OK)
        
        # 2. Submit KYC
        kyc_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        }
        
        kyc_response = self.client.post('/api/compliance/kyc/profile/', kyc_data, format='json')
        self.assertEqual(kyc_response.status_code, status.HTTP_201_CREATED)
        
        # 3. Setup HD wallet
        wallet_data = {
            'password': 'testpass123'
        }
        
        wallet_response = self.client.post('/api/wallet/setup/hd/', wallet_data, format='json')
        self.assertEqual(wallet_response.status_code, status.HTTP_200_OK)
        
        # 4. Deposit funds
        deposit_data = {
            'amount': '1000.00',
            'idempotency_key': 'test-deposit-integration'
        }
        
        deposit_response = self.client.post('/api/wallet/deposit/', deposit_data, format='json')
        self.assertEqual(deposit_response.status_code, status.HTTP_201_CREATED)
        
        # 5. Place trading order
        trading_pair = TradingPair.objects.create(
            base_currency='BTC',
            quote_currency='USD',
            symbol='BTC-USD',
            min_order_size=Decimal('0.001'),
            max_order_size=Decimal('100')
        )
        
        order_data = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'size': '0.1',
            'order_type': 'limit',
            'price': '50000.00'
        }
        
        order_response = self.client.post('/api/trading/orders/', order_data, format='json')
        self.assertEqual(order_response.status_code, status.HTTP_201_CREATED)
        
        # 6. Verify order was placed
        orders_response = self.client.get('/api/trading/orders/')
        self.assertEqual(orders_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(orders_response.data['orders']), 1)
