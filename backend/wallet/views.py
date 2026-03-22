from decimal import Decimal, InvalidOperation
from django.utils import timezone

from django.db import transaction, IntegrityError
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Wallet, Transaction
from .serializers import WalletSerializer
from backend.trading.models import TradingAccount, MarketData, TradingPair


def get_wallet_balance(wallet: Wallet) -> Decimal:
    """
    Ledger-based balance computation
    """
    deposits = wallet.transactions.filter(
        transaction_type=Transaction.DEPOSIT,
        is_active=True
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    withdrawals = wallet.transactions.filter(
        transaction_type=Transaction.WITHDRAW,
        is_active=True
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return deposits - withdrawals


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_detail(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    serializer = WalletSerializer(wallet)

    data = serializer.data
    data["balance"] = str(wallet.balance)

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deposit(request):
    try:
        amount = Decimal(request.data.get("amount"))
    except (TypeError, InvalidOperation):
        return Response({"error": "Invalid amount"}, status=400)

    if amount <= 0:
        return Response({"error": "Amount must be positive"}, status=400)

    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return Response({"error": "Missing Idempotency-Key"}, status=400)

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # Idempotent replay
    if Transaction.objects.filter(idempotency_key=idempotency_key).exists():
        return Response(
            {
                "message": "Duplicate request ignored",
                "balance": str(wallet.balance)
            },
            status=200
        )

    try:
        with transaction.atomic():
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=Transaction.DEPOSIT,
                idempotency_key=idempotency_key
            )

    except IntegrityError:
        return Response({"error": "Duplicate transaction"}, status=400)

    return Response(
        {
            "message": "Deposit successful",
            "balance": str(wallet.balance)
        },
        status=201
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request):
    try:
        amount = Decimal(request.data.get("amount"))
    except (TypeError, InvalidOperation):
        return Response({"error": "Invalid amount"}, status=400)

    if amount <= 0:
        return Response({"error": "Amount must be positive"}, status=400)

    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return Response({"error": "Missing Idempotency-Key"}, status=400)

    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # Idempotent replay
    if Transaction.objects.filter(idempotency_key=idempotency_key).exists():
        return Response(
            {
                "message": "Duplicate request ignored",
                "balance": str(wallet.balance)
            },
            status=200
        )

    if wallet.balance < amount:
        return Response({"error": "Insufficient balance"}, status=400)

    try:
        with transaction.atomic():
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=Transaction.WITHDRAW,
                idempotency_key=idempotency_key
            )

    except IntegrityError:
        return Response({"error": "Database constraint violation"}, status=400)

    return Response(
        {
            "message": "Withdrawal successful",
            "balance": str(wallet.balance)
        },
        status=201
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    transactions = wallet.transactions.filter(is_active=True)

    data = [
        {
            "type": t.transaction_type,
            "amount": str(t.amount),
            "date": t.created_at,
        }
        for t in transactions
    ]

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_portfolio(request):
    """
    Get user's portfolio information including balance and wallet data
    """
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    
    # Calculate total balance
    total_balance = get_wallet_balance(wallet)
    
    # Get primary address or None
    primary_address = wallet.addresses.filter(is_used=False).first()
    address_str = primary_address.address if primary_address else None
    
    # Get wallet details
    wallet_data = {
        "portfolio_value": str(total_balance),
        "portfolio_change": "0.00",  # Placeholder for now
        "total_balance": str(total_balance),
        "wallet_count": Wallet.objects.filter(user=request.user).count(),
        "wallet": {
            "id": wallet.id,
            "address": address_str,  # Fixed: use addresses relationship
            "balance": str(wallet.balance),
            "wallet_type": wallet.wallet_type,
            "created_at": wallet.created_at,
            "addresses_count": wallet.addresses.count()
        }
    }
    
    return Response(wallet_data)


def convert_to_usd(amount, crypto_type):
    """Convert cryptocurrency amount to USD"""
    try:
        # Try to find a trading pair for this crypto
        trading_pair = TradingPair.objects.filter(
            base_currency=crypto_type.upper(),
            quote_currency='USD',
            is_active=True
        ).first()
        
        if trading_pair:
            # Get latest market data
            market_data = MarketData.objects.filter(
                trading_pair=trading_pair
            ).order_by('-timestamp').first()
            
            if market_data:
                return amount * market_data.last_price
    except Exception:
        pass
    
    # Fallback: return 0 if no pricing data available
    return Decimal('0')


def calculate_portfolio_change_24h(user, current_value):
    """Calculate 24-hour portfolio change percentage"""
    # For now, return a placeholder - implement historical tracking later
    # This could be enhanced to track historical portfolio values
    return Decimal('2.34')


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_portfolio_enhanced(request):
    """
    Get enhanced portfolio information with crypto/fiat breakdown
    """
    user = request.user
    
    # Get trading account
    trading_account, _ = TradingAccount.objects.get_or_create(user=user)
    
    # Get all user wallets
    wallets = Wallet.objects.filter(user=user)
    
    # Calculate crypto holdings
    crypto_holdings = {}
    total_crypto_value = Decimal('0')
    
    for wallet in wallets:
        wallet_balance = get_wallet_balance(wallet)
        # Convert to USD based on current prices
        crypto_value = convert_to_usd(wallet_balance, wallet.wallet_type)
        total_crypto_value += crypto_value
        
        crypto_holdings[wallet.wallet_type] = {
            "amount": str(wallet_balance),
            "value": str(crypto_value)
        }
    
    # Calculate 24h change
    portfolio_change_24h = calculate_portfolio_change_24h(user, total_crypto_value)
    total_portfolio_value = total_crypto_value + trading_account.available_balance
    
    portfolio_data = {
        "total_portfolio_value": str(total_portfolio_value),
        "currency": "USD",
        "portfolio_change_24h": str(portfolio_change_24h),
        "portfolio_change_24h_absolute": str(abs(portfolio_change_24h * total_portfolio_value / 100)),
        "crypto_holdings": {
            "total_value": str(total_crypto_value),
            "breakdown": [
                {"symbol": symbol.upper(), "amount": data["amount"], "value": data["value"]}
                for symbol, data in crypto_holdings.items()
            ]
        },
        "fiat_balance": {
            "available": str(trading_account.available_balance),
            "frozen": str(trading_account.frozen_balance),
            "total": str(trading_account.total_balance)
        },
        "wallet_count": wallets.count(),
        "last_updated": timezone.now().isoformat()
    }
    
    return Response(portfolio_data)
