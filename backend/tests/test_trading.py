from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from backend.trading.models import TradingPair, Order, Trade, TradingAccount
from backend.trading.engine import TradingEngine

User = get_user_model()

class TradingEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='trader',
            email='trader@example.com',
            password='testpass123'
        )
        
        self.trading_pair = TradingPair.objects.create(
            base_currency='BTC',
            quote_currency='USD',
            symbol='BTC-USD',
            min_order_size=Decimal('0.001'),
            max_order_size=Decimal('100'),
            price_precision=2,
            size_precision=8
        )
        
        self.engine = TradingEngine()
    
    def test_place_limit_order(self):
        order_data = {
            'user': self.user,
            'trading_pair': self.trading_pair,
            'order_type': 'limit',
            'side': 'buy',
            'size': Decimal('1.0'),
            'price': Decimal('50000.00')
        }
        
        result = self.engine.place_order(order_data)
        self.assertTrue(result['success'])
        self.assertEqual(result['order'].status, 'open')
    
    def test_order_matching(self):
        # Place a buy order
        buy_order_data = {
            'user': self.user,
            'trading_pair': self.trading_pair,
            'order_type': 'limit',
            'side': 'buy',
            'size': Decimal('1.0'),
            'price': Decimal('50000.00')
        }
        
        buy_result = self.engine.place_order(buy_order_data)
        self.assertTrue(buy_result['success'])
        
        # Place a matching sell order
        sell_order_data = {
            'user': self.user,
            'trading_pair': self.trading_pair,
            'order_type': 'limit',
            'side': 'sell',
            'size': Decimal('1.0'),
            'price': Decimal('50000.00')
        }
        
        sell_result = self.engine.place_order(sell_order_data)
        self.assertTrue(sell_result['success'])
        
        # Check if trade was created
        trades = Trade.objects.filter(
            trading_pair=self.trading_pair
        )
        self.assertEqual(trades.count(), 1)
    
    def test_order_cancellation(self):
        # Place an order first
        order_data = {
            'user': self.user,
            'trading_pair': self.trading_pair,
            'order_type': 'limit',
            'side': 'buy',
            'size': Decimal('1.0'),
            'price': Decimal('50000.00')
        }
        
        result = self.engine.place_order(order_data)
        order_id = result['order'].id
        
        # Cancel the order
        cancel_result = self.engine.cancel_order(order_id, self.user)
        self.assertTrue(cancel_result['success'])
        self.assertEqual(cancel_result['order'].status, 'cancelled')
    
    def test_order_book_snapshot(self):
        # Place some orders
        order_data = {
            'user': self.user,
            'trading_pair': self.trading_pair,
            'order_type': 'limit',
            'side': 'buy',
            'size': Decimal('1.0'),
            'price': Decimal('50000.00')
        }
        
        self.engine.place_order(order_data)
        
        # Get order book snapshot
        snapshot = self.engine.get_order_book_snapshot(self.trading_pair)
        self.assertIn('bids', snapshot)
        self.assertIn('asks', snapshot)
        self.assertIn('sequence', snapshot)


class TradingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='trader',
            email='trader@example.com',
            password='testpass123'
        )
        
        self.trading_pair = TradingPair.objects.create(
            base_currency='BTC',
            quote_currency='USD',
            symbol='BTC-USD',
            min_order_size=Decimal('0.001'),
            max_order_size=Decimal('100')
        )
    
    def test_trading_pair_creation(self):
        self.assertEqual(self.trading_pair.symbol, 'BTC-USD')
        self.assertEqual(self.trading_pair.base_currency, 'BTC')
        self.assertEqual(self.trading_pair.quote_currency, 'USD')
    
    def test_order_creation(self):
        order = Order.objects.create(
            user=self.user,
            trading_pair=self.trading_pair,
            order_type='limit',
            side='buy',
            size=Decimal('1.0'),
            price=Decimal('50000.00')
        )
        
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.side, 'buy')
    
    def test_trading_account_creation(self):
        account = TradingAccount.objects.create(user=self.user)
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.total_balance, Decimal('0'))
        self.assertEqual(account.total_trades, 0)
