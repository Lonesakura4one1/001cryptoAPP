import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import Order, Trade, OrderBook, MarketData, TradingAccount


class OrderBookEngine:
    """Central Limit Order Book (CLOB) engine"""
    
    def __init__(self, trading_pair):
        self.trading_pair = trading_pair
        self.bids = {}  # Buy orders sorted by price descending
        self.asks = {}  # Sell orders sorted by price ascending
        self.sequence = 0
    
    def add_order(self, order):
        """Add order to order book"""
        if order.side == 'buy':
            if order.price not in self.bids:
                self.bids[order.price] = []
            self.bids[order.price].append(order)
            # Sort bids by price descending
            self.bids[order.price].sort(key=lambda x: x.created_at)
        else:
            if order.price not in self.asks:
                self.asks[order.price] = []
            self.asks[order.price].append(order)
            # Sort asks by price ascending
            self.asks[order.price].sort(key=lambda x: x.created_at)
        
        self.sequence += 1
        return self.sequence
    
    def remove_order(self, order):
        """Remove order from order book"""
        if order.side == 'buy':
            if order.price in self.bids:
                self.bids[order.price] = [
                    o for o in self.bids[order.price] if o.id != order.id
                ]
                if not self.bids[order.price]:
                    del self.bids[order.price]
        else:
            if order.price in self.asks:
                self.asks[order.price] = [
                    o for o in self.asks[order.price] if o.id != order.id
                ]
                if not self.asks[order.price]:
                    del self.asks[order.price]
        
        self.sequence += 1
        return self.sequence
    
    def get_best_bid(self):
        """Get best bid price"""
        if not self.bids:
            return None
        return max(self.bids.keys())
    
    def get_best_ask(self):
        """Get best ask price"""
        if not self.asks:
            return None
        return min(self.asks.keys())
    
    def get_spread(self):
        """Get bid-ask spread"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
    
    def to_dict(self):
        """Convert order book to dictionary"""
        # Sort bids by price descending
        sorted_bids = sorted(
            [(price, len(orders), sum(o.size for o in orders))
             for price, orders in self.bids.items()],
            key=lambda x: x[0],
            reverse=True
        )
        
        # Sort asks by price ascending
        sorted_asks = sorted(
            [(price, len(orders), sum(o.size for o in orders))
             for price, orders in self.asks.items()],
            key=lambda x: x[0]
        )
        
        return {
            'bids': sorted_bids[:20],  # Top 20 levels
            'asks': sorted_asks[:20],  # Top 20 levels
            'spread': self.get_spread(),
            'sequence': self.sequence
        }


class TradingEngine:
    """Main trading engine"""
    
    def __init__(self):
        self.order_books = {}  # One order book per trading pair
    
    def get_order_book(self, trading_pair):
        """Get or create order book for trading pair"""
        if trading_pair.symbol not in self.order_books:
            self.order_books[trading_pair.symbol] = OrderBookEngine(trading_pair)
        return self.order_books[trading_pair.symbol]
    
    @transaction.atomic
    def place_order(self, order_data):
        """Place new order and attempt to match"""
        try:
            # Create order
            order = Order.objects.create(
                user=order_data['user'],
                trading_pair=order_data['trading_pair'],
                order_type=order_data['order_type'],
                side=order_data['side'],
                size=order_data['size'],
                price=order_data.get('price'),
                stop_price=order_data.get('stop_price'),
                time_in_force=order_data.get('time_in_force', 'GTC'),
                client_order_id=order_data.get('client_order_id')
            )
            
            # Validate user balance
            if not self._validate_balance(order):
                order.status = 'rejected'
                order.save()
                return {'success': False, 'error': 'Insufficient balance', 'order': order}
            
            # Process order
            if order.order_type == 'market':
                result = self._process_market_order(order)
            else:
                result = self._process_limit_order(order)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _validate_balance(self, order):
        """Validate user has sufficient balance"""
        try:
            account = TradingAccount.objects.get(user=order.user)
            
            if order.side == 'buy':
                # Need enough quote currency
                required = order.size * (order.price or Decimal('0'))
                return account.available_balance >= required
            else:
                # Need enough base currency
                return account.available_balance >= order.size
                
        except TradingAccount.DoesNotExist:
            return False
    
    def _process_market_order(self, order):
        """Process market order"""
        order_book = self.get_order_book(order.trading_pair)
        
        if order.side == 'buy':
            # Match with asks
            matches = self._match_market_order(order, order_book.asks, 'sell')
        else:
            # Match with bids
            matches = self._match_market_order(order, order_book.bids, 'buy')
        
        if matches:
            order.status = 'filled'
            order.filled_size = order.size
            order.filled_at = timezone.now()
            order.save()
            
            # Create trades
            for match in matches:
                self._create_trade(order, match['order'], match['size'], match['price'])
            
            return {'success': True, 'order': order, 'trades': matches}
        else:
            order.status = 'rejected'
            order.save()
            return {'success': False, 'error': 'No matching orders', 'order': order}
    
    def _process_limit_order(self, order):
        """Process limit order"""
        order_book = self.get_order_book(order.trading_pair)
        
        # Add to order book
        order_book.add_order(order)
        order.status = 'open'
        order.save()
        
        # Try to match
        matches = []
        
        if order.side == 'buy':
            # Match with asks at or below order price
            matching_prices = [p for p in order_book.asks.keys() if p <= order.price]
            for price in sorted(matching_prices):
                for ask_order in order_book.asks[price]:
                    if order.filled_size >= order.size:
                        break
                    
                    match_size = min(
                        order.size - order.filled_size,
                        ask_order.size - ask_order.filled_size
                    )
                    
                    matches.append({
                        'order': ask_order,
                        'size': match_size,
                        'price': price
                    })
                    
                    # Update filled sizes
                    order.filled_size += match_size
                    ask_order.filled_size += match_size
                    
                    # Remove fully filled orders
                    if ask_order.filled_size >= ask_order.size:
                        order_book.remove_order(ask_order)
                        ask_order.status = 'filled'
                        ask_order.filled_at = timezone.now()
                        ask_order.save()
        else:
            # Match with bids at or above order price
            matching_prices = [p for p in order_book.bids.keys() if p >= order.price]
            for price in sorted(matching_prices, reverse=True):
                for bid_order in order_book.bids[price]:
                    if order.filled_size >= order.size:
                        break
                    
                    match_size = min(
                        order.size - order.filled_size,
                        bid_order.size - bid_order.filled_size
                    )
                    
                    matches.append({
                        'order': bid_order,
                        'size': match_size,
                        'price': price
                    })
                    
                    # Update filled sizes
                    order.filled_size += match_size
                    bid_order.filled_size += match_size
                    
                    # Remove fully filled orders
                    if bid_order.filled_size >= bid_order.size:
                        order_book.remove_order(bid_order)
                        bid_order.status = 'filled'
                        bid_order.filled_at = timezone.now()
                        bid_order.save()
        
        # Update order status
        if order.filled_size >= order.size:
            order.status = 'filled'
            order.filled_at = timezone.now()
            order_book.remove_order(order)
        elif order.filled_size > 0:
            order.status = 'partially_filled'
        
        order.save()
        
        # Create trades
        for match in matches:
            self._create_trade(order, match['order'], match['size'], match['price'])
        
        return {'success': True, 'order': order, 'trades': matches}
    
    def _match_market_order(self, order, order_book_side, side):
        """Match market order against order book side"""
        matches = []
        
        if side == 'sell':
            # Buy order matches with asks (sorted by price ascending)
            sorted_prices = sorted(order_book_side.keys())
        else:
            # Sell order matches with bids (sorted by price descending)
            sorted_prices = sorted(order_book_side.keys(), reverse=True)
        
        for price in sorted_prices:
            for book_order in order_book_side[price]:
                if order.filled_size >= order.size:
                    break
                
                match_size = min(
                    order.size - order.filled_size,
                    book_order.size - book_order.filled_size
                )
                
                matches.append({
                    'order': book_order,
                    'size': match_size,
                    'price': price
                })
                
                # Update filled sizes
                order.filled_size += match_size
                book_order.filled_size += match_size
                
                # Remove fully filled orders
                if book_order.filled_size >= book_order.size:
                    book_order.status = 'filled'
                    book_order.filled_at = timezone.now()
                    book_order.save()
        
        return matches
    
    def _create_trade(self, taker_order, maker_order, size, price):
        """Create trade record"""
        trade = Trade.objects.create(
            taker_order=taker_order,
            maker_order=maker_order,
            trading_pair=taker_order.trading_pair,
            size=size,
            price=price,
            taker_fee=size * taker_order.trading_pair.taker_fee,
            maker_fee=size * maker_order.trading_pair.maker_fee
        )
        
        # Update order averages
        self._update_order_average(taker_order, size, price)
        self._update_order_average(maker_order, size, price)
        
        return trade
    
    def _update_order_average(self, order, size, price):
        """Update order average price"""
        if order.average_price is None:
            order.average_price = price
        else:
            total_size = order.filled_size
            order.average_price = (
                (order.average_price * (total_size - size) + price * size) / total_size
            )
        order.save()
    
    def cancel_order(self, order_id, user):
        """Cancel order"""
        try:
            order = Order.objects.get(id=order_id, user=user, status__in=['open', 'partially_filled'])
            
            # Remove from order book
            order_book = self.get_order_book(order.trading_pair)
            order_book.remove_order(order)
            
            # Update status
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            
            return {'success': True, 'order': order}
            
        except Order.DoesNotExist:
            return {'success': False, 'error': 'Order not found'}
    
    def get_order_book_snapshot(self, trading_pair):
        """Get current order book snapshot"""
        order_book = self.get_order_book(trading_pair)
        snapshot = order_book.to_dict()
        
        # Save to database
        OrderBook.objects.create(
            trading_pair=trading_pair,
            bids=snapshot['bids'],
            asks=snapshot['asks'],
            sequence=snapshot['sequence']
        )
        
        return snapshot
