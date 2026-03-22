from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ExternalTransaction, CryptoPrice
from .api_clients import get_exchange_client


@api_view(["GET"])
@permission_classes([])
def public_prices(request):
    """Public endpoint for crypto prices - no auth required"""
    prices = CryptoPrice.objects.all().order_by('-last_updated')
    
    data = []
    for price in prices:
        # Add mock 24h change data
        import random
        change_24h = round(random.uniform(-10, 10), 2)
        
        data.append({
            'symbol': price.symbol,
            'price_usd': str(price.usd_price),
            'change_24h': str(change_24h),
            'source': price.source,
            'last_updated': price.last_updated
        })
    
    return Response(data)


@api_view(["GET"])
def get_crypto_price(request, symbol):
    """Get current price for a cryptocurrency"""
    exchange = request.GET.get('exchange', 'coingecko')
    
    try:
        client = get_exchange_client(exchange)
        price = client.get_price(symbol)
        
        # Cache the price
        CryptoPrice.objects.update_or_create(
            symbol=symbol.upper(),
            source=exchange,
            defaults={'usd_price': price}
        )
        
        return Response({
            'symbol': symbol.upper(),
            'price': str(price),
            'source': exchange
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(["GET"])
def list_crypto_prices(request):
    """List cached cryptocurrency prices"""
    prices = CryptoPrice.objects.all().order_by('-last_updated')
    
    data = [
        {
            'symbol': price.symbol,
            'price': str(price.usd_price),
            'source': price.source,
            'last_updated': price.last_updated
        }
        for price in prices
    ]
    
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buy_crypto(request):
    """Buy cryptocurrency (placeholder for real exchange integration)"""
    symbol = request.data.get('symbol')
    amount = request.data.get('amount')
    exchange = request.data.get('exchange', 'binance')
    
    try:
        symbol = symbol.upper()
        amount = Decimal(str(amount))
        
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        
        # Get current price
        client = get_exchange_client('coingecko')  # Use free API for price
        current_price = client.get_price(symbol)
        total_cost = amount * current_price
        
        # Create external transaction record
        transaction = ExternalTransaction.objects.create(
            user=request.user,
            exchange=exchange,
            external_id=f"pending_{timezone.now().timestamp()}",
            transaction_type=ExternalTransaction.BUY,
            cryptocurrency=symbol,
            amount=amount,
            price=current_price,
            total_cost=total_cost,
            status=ExternalTransaction.PENDING
        )
        
        return Response({
            'message': 'Buy order created (pending real exchange integration)',
            'transaction_id': transaction.id,
            'symbol': symbol,
            'amount': str(amount),
            'price': str(current_price),
            'total_cost': str(total_cost),
            'status': transaction.status
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sell_crypto(request):
    """Sell cryptocurrency (placeholder for real exchange integration)"""
    symbol = request.data.get('symbol')
    amount = request.data.get('amount')
    exchange = request.data.get('exchange', 'binance')
    
    try:
        symbol = symbol.upper()
        amount = Decimal(str(amount))
        
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=400)
        
        # Get current price
        client = get_exchange_client('coingecko')  # Use free API for price
        current_price = client.get_price(symbol)
        total_cost = amount * current_price
        
        # Create external transaction record
        transaction = ExternalTransaction.objects.create(
            user=request.user,
            exchange=exchange,
            external_id=f"pending_{timezone.now().timestamp()}",
            transaction_type=ExternalTransaction.SELL,
            cryptocurrency=symbol,
            amount=amount,
            price=current_price,
            total_cost=total_cost,
            status=ExternalTransaction.PENDING
        )
        
        return Response({
            'message': 'Sell order created (pending real exchange integration)',
            'transaction_id': transaction.id,
            'symbol': symbol,
            'amount': str(amount),
            'price': str(current_price),
            'total_cost': str(total_cost),
            'status': transaction.status
        }, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def external_transaction_history(request):
    """Get external crypto transaction history"""
    transactions = ExternalTransaction.objects.filter(user=request.user).order_by('-created_at')
    
    data = [
        {
            'id': t.id,
            'exchange': t.exchange,
            'type': t.transaction_type,
            'cryptocurrency': t.cryptocurrency,
            'amount': str(t.amount),
            'price': str(t.price),
            'total_cost': str(t.total_cost),
            'status': t.status,
            'created_at': t.created_at,
            'completed_at': t.completed_at
        }
        for t in transactions
    ]
    
    return Response(data)
