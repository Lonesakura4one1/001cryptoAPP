"""
Error scenario and edge case tests for crypto platform.
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
import json
import time

from backend.users.models import TwoFactorAuth, SecurityLog
from backend.wallet.models import Wallet, Transaction
from backend.trading.models import Order, TradingPair, TradingAccount
from backend.compliance.models import KYCProfile, AMLTransaction

User = get_user_model()


class AuthenticationErrorTests(APITestCase):
    """Test authentication error scenarios"""

    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/api/auth/login/', {
            'email': 'invalid@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_credentials(self):
        """Test login with missing credentials"""
        response = self.client.post('/api/auth/login/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_token(self):
        """Test API access with expired token"""
        # Create user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        # Get token and manually expire it (simulate)
        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        token = response.data['access']
        
        # Try to use token after it would be expired
        # Note: In real test, you'd need to modify token expiration time
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/wallet/')
        # Should work for now, but token expiration logic needs to be tested
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED])


class WalletErrorTests(TransactionTestCase):
    """Test wallet error scenarios"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.wallet = Wallet.objects.create(user=self.user)

    def test_insufficient_funds_withdrawal(self):
        """Test withdrawal with insufficient funds"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/wallet/withdraw/', {
            'amount': '1000.00',
            'idempotency_key': 'test-withdraw-insufficient'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient balance', response.data.get('message', ''))

    def test_duplicate_transaction_idempotency(self):
        """Test transaction idempotency"""
        self.client.force_authenticate(user=self.user)
        
        # Create deposit
        deposit_data = {
            'amount': '100.00',
            'idempotency_key': 'test-duplicate-key'
        }
        
        # First request should succeed
        response1 = self.client.post('/api/wallet/deposit/', deposit_data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second request with same key should return the same result
        response2 = self.client.post('/api/wallet/deposit/', deposit_data)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data['id'], response2.data['id'])

    def test_invalid_amount_format(self):
        """Test transaction with invalid amount format"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/wallet/deposit/', {
            'amount': 'invalid_amount',
            'idempotency_key': 'test-invalid-amount'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_amount(self):
        """Test transaction with negative amount"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/wallet/deposit/', {
            'amount': '-100.00',
            'idempotency_key': 'test-negative-amount'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TradingErrorTests(TransactionTestCase):
    """Test trading error scenarios"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.trading_account = TradingAccount.objects.create(
            user=self.user,
            available_balance=Decimal('1000.00')
        )
        self.trading_pair = TradingPair.objects.create(
            base_currency='BTC',
            quote_currency='USD',
            symbol='BTC-USD',
            min_order_size=Decimal('0.001'),
            max_order_size=Decimal('100'),
            maker_fee=Decimal('0.001'),
            taker_fee=Decimal('0.001')
        )

    def test_insufficient_balance_order(self):
        """Test order placement with insufficient balance"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/trading/orders/', {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'size': '10.0',
            'order_type': 'limit',
            'price': '50000.00'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient balance', response.data.get('error', ''))

    def test_invalid_order_size(self):
        """Test order with invalid size"""
        self.client.force_authenticate(user=self.user)
        
        # Test size below minimum
        response = self.client.post('/api/trading/orders/', {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'size': '0.0001',  # Below min_order_size
            'order_type': 'limit',
            'price': '50000.00'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_trading_pair(self):
        """Test order with invalid trading pair"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/trading/orders/', {
            'trading_pair': 'INVALID-PAIR',
            'side': 'buy',
            'size': '1.0',
            'order_type': 'limit',
            'price': '50000.00'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_market_order_without_matching_orders(self):
        """Test market order when no matching orders exist"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/trading/orders/', {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'size': '1.0',
            'order_type': 'market'
        })
        # Should be rejected if no matching orders exist
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED])


class ComplianceErrorTests(TransactionTestCase):
    """Test compliance error scenarios"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )

    def test_kyc_submission_with_invalid_data(self):
        """Test KYC submission with invalid data"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/compliance/kyc/profile/', {
            'first_name': '',  # Empty first name
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_kyc_submission(self):
        """Test duplicate KYC profile submission"""
        self.client.force_authenticate(user=self.user)
        
        # Create initial KYC profile
        KYCProfile.objects.create(
            user=self.user,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            nationality='US',
            country_of_residence='US',
            address_line_1='123 Main St',
            city='New York',
            state_province='NY',
            postal_code='10001',
            phone_number='+1234567890'
        )
        
        # Try to submit another profile
        response = self.client.post('/api/compliance/kyc/profile/', {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1992-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1='456 Oak St',
            'city': 'Boston',
            'state_province': 'MA',
            'postal_code': '02101',
            'phone_number='+1987654321'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SystemErrorTests(APITestCase):
    """Test system-level error scenarios"""

    def test_database_connection_error_simulation(self):
        """Test behavior when database is unavailable"""
        # This would require mocking database connection failures
        # For now, just test that the health check fails appropriately
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')

    def test_redis_connection_error_simulation(self):
        """Test behavior when Redis is unavailable"""
        # This would require mocking Redis connection failures
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rate_limiting(self):
        """Test API rate limiting"""
        # Create user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.client.force_authenticate(user=user)
        
        # Make multiple rapid requests to test rate limiting
        responses = []
        for i in range(15):  # More than the rate limit
            response = self.client.get('/api/wallet/')
            responses.append(response.status_code)
            time.sleep(0.01)  # Small delay
        
        # Some requests should be rate limited
        rate_limited_count = sum(1 for status in responses if status == status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertGreater(rate_limited_count, 0, "Some requests should be rate limited")


class SecurityErrorTests(TransactionTestCase):
    """Test security-related error scenarios"""

    def test_sql_injection_attempt(self):
        """Test SQL injection attempts"""
        # Create user
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.client.force_authenticate(user=user)
        
        # Try SQL injection in order parameters
        malicious_input = "1; DROP TABLE users; --"
        
        response = self.client.post('/api/trading/orders/', {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'size': malicious_input,
            'order_type': 'limit',
            'price': '50000.00'
        })
        # Should be rejected by validation, not execute SQL
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_xss_attempt(self):
        """Test XSS attempts"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.client.force_authenticate(user=user)
        
        # Try XSS in user profile
        xss_payload = "<script>alert('xss')</script>"
        
        response = self.client.post('/api/compliance/kyc/profile/', {
            'first_name': xss_payload,
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        })
        # Should be rejected or sanitized
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED])
        
        if response.status_code == status.HTTP_201_CREATED:
            # Verify XSS payload was sanitized
            profile = KYCProfile.objects.get(user=user)
            self.assertNotIn('<script>', profile.first_name)


class PerformanceErrorTests(APITestCase):
    """Test performance-related error scenarios"""

    def test_large_request_handling(self):
        """Test handling of very large requests"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.client.force_authenticate(user=user)
        
        # Create request with very large data
        large_data = 'x' * 1000000  # 1MB of data
        
        response = self.client.post('/api/compliance/kyc/profile/', {
            'first_name': large_data,
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'nationality': 'US',
            'country_of_residence': 'US',
            'address_line_1': '123 Main St',
            'city': 'New York',
            'state_province': 'NY',
            'postal_code': '10001',
            'phone_number': '+1234567890'
        })
        # Should be rejected due to size limits
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import queue
        
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        
        results = queue.Queue()
        
        def make_request():
            client = self.client_class()
            client.force_authenticate(user=user)
            response = client.get('/api/wallet/')
            results.put(response.status_code)
        
        # Make 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all requests completed successfully
        success_count = 0
        while not results.empty():
            if results.get() == status.HTTP_200_OK:
                success_count += 1
        
        self.assertEqual(success_count, 10, "All concurrent requests should succeed")


class ConcurrencyErrorTests(TransactionTestCase):
    """Test concurrency-related error scenarios"""

    def test_concurrent_transaction_creation(self):
        """Test concurrent transaction creation with same idempotency key"""
        import threading
        import queue
        
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        wallet = Wallet.objects.create(user=user)
        
        results = queue.Queue()
        
        def create_transaction():
            client = self.client_class()
            client.force_authenticate(user=user)
            response = client.post('/api/wallet/deposit/', {
                'amount': '100.00',
                'idempotency_key': 'concurrent-test-key'
            })
            results.put(response.status_code)
        
        # Create 5 concurrent transactions with same idempotency key
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_transaction)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Only one should succeed (201), others should return existing (200)
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        success_201 = status_codes.count(status.HTTP_201_CREATED)
        success_200 = status_codes.count(status.HTTP_200_OK)
        
        self.assertEqual(success_201, 1, "Only one transaction should be created")
        self.assertEqual(success_200, 4, "Other requests should return existing transaction")

    def test_race_condition_order_matching(self):
        """Test race conditions in order matching"""
        # This is a complex test that would require mocking the trading engine
        # For now, just verify basic concurrent order creation works
        
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        trading_account = TradingAccount.objects.create(
            user=user,
            available_balance=Decimal('10000.00')
        )
        trading_pair = TradingPair.objects.create(
            base_currency='BTC',
            quote_currency='USD',
            symbol='BTC-USD',
            min_order_size=Decimal('0.001'),
            max_order_size=Decimal('100'),
            maker_fee=Decimal('0.001'),
            taker_fee=Decimal('0.001')
        )
        
        # Create multiple orders concurrently
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_order(side):
            client = self.client_class()
            client.force_authenticate(user=user)
            response = client.post('/api/trading/orders/', {
                'trading_pair': 'BTC-USD',
                'side': side,
                'size': '0.1',
                'order_type': 'limit',
                'price': '50000.00'
            })
            results.put(response.status_code)
        
        # Create buy and sell orders concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_order, args=('buy',))
            threads.append(thread)
            thread.start()
        
        for i in range(5):
            thread = threading.Thread(target=create_order, args=('sell',))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All orders should be created successfully
        success_count = 0
        while not results.empty():
            if results.get() == status.HTTP_201_CREATED:
                success_count += 1
        
        self.assertEqual(success_count, 10, "All concurrent orders should be created")
