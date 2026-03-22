import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from backend.trading.models import TradingPair, Order, Trade
from backend.trading.engine import TradingEngine
import asyncio


class MarketDataConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time market data"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        self.trading_pair = None
        
        if isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return
        
        await self.accept()
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to market data stream',
            'timestamp': str(timezone.now())
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.trading_pair:
            # Leave trading pair room
            await self.channel_layer.group_discard(
                f"market_{self.trading_pair.symbol}",
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                await self.handle_subscribe(data)
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def handle_subscribe(self, data):
        """Handle subscription requests"""
        symbol = data.get('symbol')
        channels = data.get('channels', [])
        
        if not symbol:
            await self.send_error("Symbol is required for subscription")
            return
        
        # Get trading pair
        try:
            trading_pair = await database_sync_to_async(
                TradingPair.objects.get
            )(symbol=symbol, is_active=True)
        except TradingPair.DoesNotExist:
            await self.send_error(f"Invalid trading pair: {symbol}")
            return
        
        self.trading_pair = trading_pair
        
        # Join trading pair room
        await self.channel_layer.group_add(
            f"market_{symbol}",
            self.channel_name
        )
        
        # Send current market data
        await self.send_market_data(symbol)
        
        # Send subscription confirmation
        await self.send(text_data=json.dumps({
            'type': 'subscription',
            'symbol': symbol,
            'channels': channels,
            'status': 'subscribed',
            'timestamp': str(timezone.now())
        }))
    
    async def handle_unsubscribe(self, data):
        """Handle unsubscription requests"""
        symbol = data.get('symbol')
        
        if symbol and self.trading_pair and self.trading_pair.symbol == symbol:
            # Leave trading pair room
            await self.channel_layer.group_discard(
                f"market_{symbol}",
                self.channel_name
            )
            
            await self.send(text_data=json.dumps({
                'type': 'subscription',
                'symbol': symbol,
                'status': 'unsubscribed',
                'timestamp': str(timezone.now())
            }))
    
    async def handle_ping(self):
        """Handle ping messages"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': str(timezone.now())
        }))
    
    async def send_market_data(self, symbol):
        """Send current market data"""
        try:
            # Get latest market data
            market_data = await database_sync_to_async(
                lambda: TradingPair.objects.select_related().get(
                    symbol=symbol, is_active=True
                )
            )()
            
            # Get order book snapshot
            from backend.trading.views import trading_engine
            order_book = trading_engine.get_order_book_snapshot(market_data)
            
            await self.send(text_data=json.dumps({
                'type': 'market_data',
                'symbol': symbol,
                'order_book': order_book,
                'timestamp': str(timezone.now())
            }))
            
        except Exception as e:
            await self.send_error(f"Error fetching market data: {str(e)}")
    
    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': str(timezone.now())
        }))


class OrderBookConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for order book updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to order book stream',
            'timestamp': str(timezone.now())
        }))
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_orderbook':
                await self.handle_orderbook_subscribe(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except Exception as e:
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def handle_orderbook_subscribe(self, data):
        """Handle order book subscription"""
        symbol = data.get('symbol')
        
        if not symbol:
            await self.send_error("Symbol is required")
            return
        
        # Join order book room
        await self.channel_layer.group_add(
            f"orderbook_{symbol}",
            self.channel_name
        )
        
        await self.send(text_data=json.dumps({
            'type': 'orderbook_subscription',
            'symbol': symbol,
            'status': 'subscribed',
            'timestamp': str(timezone.now())
        }))
    
    async def handle_ping(self):
        """Handle ping messages"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': str(timezone.now())
        }))
    
    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': str(timezone.now())
        }))


class TradingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for user's trading activity"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return
        
        await self.accept()
        
        # Join user's personal trading room
        await self.channel_layer.group_add(
            f"user_trades_{self.user.id}",
            self.channel_name
        )
        
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to trading stream',
            'timestamp': str(timezone.now())
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave user's trading room
        await self.channel_layer.group_discard(
            f"user_trades_{self.user.id}",
            self.channel_name
        )
    
    async def send_trade_update(self, event):
        """Send trade update to user"""
        await self.send(text_data=json.dumps({
            'type': 'trade_update',
            'trade': event['trade'],
            'timestamp': str(timezone.now())
        }))
    
    async def send_order_update(self, event):
        """Send order update to user"""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order': event['order'],
            'timestamp': str(timezone.now())
        }))
    
    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': str(timezone.now())
        }))


# Signal handlers for broadcasting updates
async def broadcast_order_update(order):
    """Broadcast order update to relevant channels"""
    channel_layer = get_channel_layer()
    
    # Send to user's trading channel
    await channel_layer.group_send(
        f"user_trades_{order.user.id}",
        {
            'type': 'send_order_update',
            'order': {
                'id': str(order.id),
                'status': order.status,
                'filled_size': str(order.filled_size),
                'average_price': str(order.average_price) if order.average_price else None
            }
        }
    )
    
    # Send to market data channels
    if order.trading_pair:
        await channel_layer.group_send(
            f"orderbook_{order.trading_pair.symbol}",
            {
                'type': 'orderbook_update',
                'order': {
                    'id': str(order.id),
                    'side': order.side,
                    'price': str(order.price) if order.price else None,
                    'size': str(order.size),
                    'status': order.status
                }
            }
        )


async def broadcast_trade_update(trade):
    """Broadcast trade update to market data channels"""
    channel_layer = get_channel_layer()
    
    # Send to both users' trading channels
    await channel_layer.group_send(
        f"user_trades_{trade.taker_order.user.id}",
        {
            'type': 'send_trade_update',
            'trade': {
                'id': str(trade.id),
                'trading_pair': trade.trading_pair.symbol,
                'size': str(trade.size),
                'price': str(trade.price),
                'side': trade.taker_order.side,
                'taker_fee': str(trade.taker_fee),
                'maker_fee': str(trade.maker_fee)
            }
        }
    )
    
    await channel_layer.group_send(
        f"user_trades_{trade.maker_order.user.id}",
        {
            'type': 'send_trade_update',
            'trade': {
                'id': str(trade.id),
                'trading_pair': trade.trading_pair.symbol,
                'size': str(trade.size),
                'price': str(trade.price),
                'side': 'buy' if trade.maker_order.side == 'buy' else 'sell',
                'taker_fee': str(trade.taker_fee),
                'maker_fee': str(trade.maker_fee)
            }
        }
    )
    
    # Send to market data channels
    await channel_layer.group_send(
        f"market_{trade.trading_pair.symbol}",
        {
            'type': 'market_update',
            'trade': {
                'id': str(trade.id),
                'size': str(trade.size),
                'price': str(trade.price),
                'timestamp': str(trade.created_at)
            }
        }
    )
