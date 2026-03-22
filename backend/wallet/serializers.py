# serializers.py
from rest_framework import serializers
from .models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ["id", "user", "balance"]

    def get_balance(self, obj):
        """
        Ledger-based balance (computed, not stored).
        """
        return str(obj.balance)


class TransactionSerializer(serializers.ModelSerializer):
    wallet = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "wallet",
            "amount",
            "transaction_type",
            "idempotency_key",
            "created_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "wallet",
            "created_at",
            "is_active",
        ]
