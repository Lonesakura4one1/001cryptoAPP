from rest_framework import serializers
from .models import ExternalTransaction, CryptoPrice


class CryptoPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoPrice
        fields = ['symbol', 'usd_price', 'source', 'last_updated']


class ExternalTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalTransaction
        fields = [
            'id',
            'exchange',
            'external_id',
            'transaction_type',
            'cryptocurrency',
            'amount',
            'price',
            'total_cost',
            'status',
            'created_at',
            'completed_at'
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'completed_at'
        ]


class BuyCryptoSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8)
    exchange = serializers.CharField(max_length=50, required=False, default='binance')


class SellCryptoSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8)
    exchange = serializers.CharField(max_length=50, required=False, default='binance')
