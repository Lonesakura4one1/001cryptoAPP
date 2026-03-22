from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid


class TradingPair(models.Model):
    """Trading pair configuration"""
    base_currency = models.CharField(max_length=10)  # BTC
    quote_currency = models.CharField(max_length=10)  # USD
    symbol = models.CharField(max_length=20, unique=True)  # BTC-USD
    
    # Trading settings
    min_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    max_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    price_precision = models.IntegerField(default=8)
    size_precision = models.IntegerField(default=8)
    
    # Fees
    maker_fee = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0010'))
    taker_fee = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0010'))
    
    # Status
    is_active = models.BooleanField(default=True)
    is_margin_trading = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['base_currency', 'quote_currency']
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.symbol


class Order(models.Model):
    """Trading order"""
    ORDER_TYPES = [
        ('market', 'Market Order'),
        ('limit', 'Limit Order'),
        ('stop', 'Stop Order'),
        ('stop_limit', 'Stop Limit'),
        ('iceberg', 'Iceberg Order'),
        ('twap', 'Time-Weighted Average Price'),
    ]
    
    SIDES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    
    STATUSES = [
        ('pending', 'Pending'),
        ('open', 'Open'),
        ('filled', 'Filled'),
        ('partially_filled', 'Partially Filled'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    TIME_IN_FORCE = [
        ('GTC', 'Good Till Cancelled'),
        ('IOC', 'Immediate Or Cancel'),
        ('FOK', 'Fill Or Kill'),
        ('GTD', 'Good Till Date'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trading_orders')
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    side = models.CharField(max_length=10, choices=SIDES)
    size = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    # Order execution
    filled_size = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    average_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    # Order settings
    time_in_force = models.CharField(max_length=3, choices=TIME_IN_FORCE, default='GTC')
    expire_time = models.DateTimeField(null=True, blank=True)
    
    # Iceberg order settings
    iceberg_display_size = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    client_order_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Fees
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    fee_currency = models.CharField(max_length=10, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['trading_pair', 'status', 'side']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client_order_id']),
        ]
    
    def __str__(self):
        return f"{self.side.upper()} {self.size} {self.trading_pair.symbol}"


class Trade(models.Model):
    """Executed trade"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Order references
    taker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='taker_trades')
    maker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='maker_trades')
    
    # Trade details
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE, related_name='trades')
    size = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Fees
    taker_fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    maker_fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['trading_pair', 'created_at']),
            models.Index(fields=['taker_order']),
            models.Index(fields=['maker_order']),
        ]
    
    def __str__(self):
        return f"{self.size} {self.trading_pair.symbol} @ {self.price}"


class OrderBook(models.Model):
    """Order book snapshot"""
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE, related_name='orderbook_snapshots')
    
    # Order book data (JSON)
    bids = models.JSONField(default=list)  # Buy orders
    asks = models.JSONField(default=list)  # Sell orders
    
    # Metadata
    sequence = models.BigIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['trading_pair', 'sequence']),
            models.Index(fields=['timestamp']),
        ]


class MarketData(models.Model):
    """Market data and statistics"""
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE, related_name='market_data')
    
    # Price data
    last_price = models.DecimalField(max_digits=20, decimal_places=8)
    bid_price = models.DecimalField(max_digits=20, decimal_places=8)
    ask_price = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Volume data
    volume_24h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    volume_1h = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Price statistics
    high_24h = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    low_24h = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['trading_pair', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]


class TradingAccount(models.Model):
    """User trading account"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trading_account')
    
    # Account balances
    available_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    frozen_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Trading statistics
    total_trades = models.IntegerField(default=0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_fees_paid = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Risk management
    margin_used = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    margin_free = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.total_balance}"
