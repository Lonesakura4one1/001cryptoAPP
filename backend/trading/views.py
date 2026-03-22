from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import models
from decimal import Decimal
from .models import Order, Trade, TradingPair, MarketData, TradingAccount
from .engine import TradingEngine


# Global trading engine instance
trading_engine = TradingEngine()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trading_pairs(request):
    """Get all available trading pairs"""
    pairs = TradingPair.objects.filter(is_active=True)
    
    return Response([
        {
            'symbol': pair.symbol,
            'base_currency': pair.base_currency,
            'quote_currency': pair.quote_currency,
            'min_order_size': str(pair.min_order_size),
            'max_order_size': str(pair.max_order_size),
            'price_precision': pair.price_precision,
            'size_precision': pair.size_precision,
            'maker_fee': str(pair.maker_fee),
            'taker_fee': str(pair.taker_fee),
            'is_margin_trading': pair.is_margin_trading
        }
        for pair in pairs
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_order(request):
    """Place new trading order"""
    try:
        data = request.data
        
        # Validate required fields
        required_fields = ['trading_pair', 'side', 'size', 'order_type']
        for field in required_fields:
            if field not in data:
                return Response({'error': f'{field} is required'}, status=400)
        
        # Get trading pair
        try:
            trading_pair = TradingPair.objects.get(symbol=data['trading_pair'], is_active=True)
        except TradingPair.DoesNotExist:
            return Response({'error': 'Invalid trading pair'}, status=400)
        
        # Validate order size
        size = Decimal(str(data['size']))
        if size < trading_pair.min_order_size or size > trading_pair.max_order_size:
            return Response({'error': 'Order size out of range'}, status=400)
        
        # Prepare order data
        order_data = {
            'user': request.user,
            'trading_pair': trading_pair,
            'order_type': data['order_type'],
            'side': data['side'],
            'size': size,
            'price': Decimal(str(data['price'])) if data.get('price') else None,
            'stop_price': Decimal(str(data['stop_price'])) if data.get('stop_price') else None,
            'time_in_force': data.get('time_in_force', 'GTC'),
            'client_order_id': data.get('client_order_id')
        }
        
        # Place order
        result = trading_engine.place_order(order_data)
        
        if result['success']:
            return Response({
                'message': 'Order placed successfully',
                'order': {
                    'id': str(result['order'].id),
                    'client_order_id': result['order'].client_order_id,
                    'trading_pair': result['order'].trading_pair.symbol,
                    'side': result['order'].side,
                    'order_type': result['order'].order_type,
                    'size': str(result['order'].size),
                    'price': str(result['order'].price) if result['order'].price else None,
                    'filled_size': str(result['order'].filled_size),
                    'average_price': str(result['order'].average_price) if result['order'].average_price else None,
                    'status': result['order'].status,
                    'created_at': result['order'].created_at
                },
                'trades': [
                    {
                        'id': str(trade.id),
                        'size': str(trade.size),
                        'price': str(trade.price),
                        'taker_fee': str(trade.taker_fee),
                        'maker_fee': str(trade.maker_fee),
                        'created_at': trade.created_at
                    }
                    for trade in result.get('trades', [])
                ]
            }, status=201)
        else:
            return Response({
                'error': result['error'],
                'order': {
                    'id': str(result['order'].id) if 'order' in result else None,
                    'status': result['order'].status if 'order' in result else None
                }
            }, status=400)
            
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel existing order"""
    try:
        result = trading_engine.cancel_order(order_id, request.user)
        
        if result['success']:
            return Response({
                'message': 'Order cancelled successfully',
                'order': {
                    'id': str(result['order'].id),
                    'status': result['order'].status,
                    'cancelled_at': result['order'].cancelled_at
                }
            })
        else:
            return Response({'error': result['error']}, status=400)
            
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders(request):
    """Get user's orders"""
    try:
        # Filter parameters
        status = request.GET.get('status')
        trading_pair = request.GET.get('trading_pair')
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Query orders
        orders = Order.objects.filter(user=request.user)
        
        if status:
            orders = orders.filter(status=status)
        if trading_pair:
            orders = orders.filter(trading_pair__symbol=trading_pair)
        
        orders = orders.order_by('-created_at')[offset:offset+limit]
        
        return Response({
            'orders': [
                {
                    'id': str(order.id),
                    'client_order_id': order.client_order_id,
                    'trading_pair': order.trading_pair.symbol,
                    'side': order.side,
                    'order_type': order.order_type,
                    'size': str(order.size),
                    'price': str(order.price) if order.price else None,
                    'filled_size': str(order.filled_size),
                    'average_price': str(order.average_price) if order.average_price else None,
                    'status': order.status,
                    'time_in_force': order.time_in_force,
                    'fee': str(order.fee),
                    'created_at': order.created_at,
                    'filled_at': order.filled_at,
                    'cancelled_at': order.cancelled_at
                }
                for order in orders
            ],
            'total': Order.objects.filter(user=request.user).count()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trades(request):
    """Get user's trades"""
    try:
        # Filter parameters
        trading_pair = request.GET.get('trading_pair')
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Query trades
        trades = Trade.objects.filter(
            models.Q(taker_order__user=request.user) | 
            models.Q(maker_order__user=request.user)
        )
        
        if trading_pair:
            trades = trades.filter(trading_pair__symbol=trading_pair)
        
        trades = trades.order_by('-created_at')[offset:offset+limit]
        
        return Response({
            'trades': [
                {
                    'id': str(trade.id),
                    'trading_pair': trade.trading_pair.symbol,
                    'size': str(trade.size),
                    'price': str(trade.price),
                    'side': 'buy' if trade.taker_order.side == 'buy' else 'sell',
                    'taker_fee': str(trade.taker_fee),
                    'maker_fee': str(trade.maker_fee),
                    'created_at': trade.created_at
                }
                for trade in trades
            ],
            'total': Trade.objects.filter(
                models.Q(taker_order__user=request.user) | 
                models.Q(maker_order__user=request.user)
            ).count()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_book(request, symbol):
    """Get order book for trading pair"""
    try:
        trading_pair = TradingPair.objects.get(symbol=symbol, is_active=True)
        order_book = trading_engine.get_order_book_snapshot(trading_pair)
        
        return Response({
            'symbol': symbol,
            'bids': order_book['bids'],
            'asks': order_book['asks'],
            'spread': str(order_book['spread']) if order_book['spread'] else None,
            'sequence': order_book['sequence']
        })
        
    except TradingPair.DoesNotExist:
        return Response({'error': 'Invalid trading pair'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_market_data(request, symbol):
    """Get market data for trading pair"""
    try:
        trading_pair = TradingPair.objects.get(symbol=symbol, is_active=True)
        
        # Get latest market data
        try:
            market_data = MarketData.objects.filter(trading_pair=trading_pair).latest('timestamp')
        except MarketData.DoesNotExist:
            market_data = None
        
        return Response({
            'symbol': symbol,
            'last_price': str(market_data.last_price) if market_data else None,
            'bid_price': str(market_data.bid_price) if market_data else None,
            'ask_price': str(market_data.ask_price) if market_data else None,
            'volume_24h': str(market_data.volume_24h) if market_data else '0',
            'high_24h': str(market_data.high_24h) if market_data and market_data.high_24h else None,
            'low_24h': str(market_data.low_24h) if market_data and market_data.low_24h else None,
            'price_change_24h': str(market_data.price_change_24h) if market_data and market_data.price_change_24h else None,
            'timestamp': market_data.timestamp if market_data else None
        })
        
    except TradingPair.DoesNotExist:
        return Response({'error': 'Invalid trading pair'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trading_account(request):
    """Get user's trading account information"""
    try:
        account, created = TradingAccount.objects.get_or_create(user=request.user)
        
        return Response({
            'available_balance': str(account.available_balance),
            'frozen_balance': str(account.frozen_balance),
            'total_balance': str(account.total_balance),
            'total_trades': account.total_trades,
            'total_volume': str(account.total_volume),
            'total_fees_paid': str(account.total_fees_paid),
            'margin_used': str(account.margin_used),
            'margin_free': str(account.margin_free)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)
