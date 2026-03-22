from django.db import models
from django.conf import settings


class ExternalTransaction(models.Model):
    """
    External crypto transactions (buy/sell from exchanges)
    """
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    )
    
    BUY = "buy"
    SELL = "sell"
    
    TRANSACTION_TYPES = (
        (BUY, "Buy"),
        (SELL, "Sell"),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='external_transactions')
    exchange = models.CharField(max_length=50)  # binance, coinbase, etc.
    external_id = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    cryptocurrency = models.CharField(max_length=20)  # BTC, ETH, etc.
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    total_cost = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.amount} {self.cryptocurrency}"


class CryptoPrice(models.Model):
    """
    Cached cryptocurrency prices from external APIs
    """
    symbol = models.CharField(max_length=20)  # BTC, ETH, etc.
    usd_price = models.DecimalField(max_digits=20, decimal_places=8)
    source = models.CharField(max_length=50)  # coinbase, binance, etc.
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['symbol', 'source']
    
    def __str__(self):
        return f"{self.symbol}: ${self.usd_price} from {self.source}"