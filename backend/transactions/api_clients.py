import requests
from decimal import Decimal
from typing import Dict, List, Optional
from django.conf import settings


class BaseCryptoExchange:
    """Base class for crypto exchange APIs"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = ""
    
    def get_price(self, symbol: str) -> Decimal:
        """Get current price for a cryptocurrency"""
        raise NotImplementedError
    
    def buy_crypto(self, symbol: str, amount: Decimal) -> Dict:
        """Buy cryptocurrency"""
        raise NotImplementedError
    
    def sell_crypto(self, symbol: str, amount: Decimal) -> Dict:
        """Sell cryptocurrency"""
        raise NotImplementedError


class CoinGeckoAPI(BaseCryptoExchange):
    """CoinGecko API for price data (free, no auth required)"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.coingecko.com/api/v3"
    
    def get_price(self, symbol: str) -> Decimal:
        """Get current price in USD"""
        try:
            # Convert symbol to CoinGecko format (BTC -> bitcoin, ETH -> ethereum)
            coin_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'LTC': 'litecoin',
                'BCH': 'bitcoin-cash',
                'ADA': 'cardano',
                'DOT': 'polkadot',
                'LINK': 'chainlink',
                'BNB': 'binancecoin',
            }
            
            coin_id = coin_map.get(symbol.upper(), symbol.lower())
            
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_last_updated_at': 'true'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            price = data[coin_id]['usd']
            
            return Decimal(str(price))
            
        except (requests.RequestException, KeyError, ValueError) as e:
            raise Exception(f"Failed to fetch price for {symbol}: {str(e)}")
    
    def buy_crypto(self, symbol: str, amount: Decimal) -> Dict:
        """CoinGecko doesn't support trading - use a real exchange"""
        raise NotImplementedError("CoinGecko only provides price data")
    
    def sell_crypto(self, symbol: str, amount: Decimal) -> Dict:
        """CoinGecko doesn't support trading - use a real exchange"""
        raise NotImplementedError("CoinGecko only provides price data")


class BinanceAPI(BaseCryptoExchange):
    """Binance API for trading (requires API keys)"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        super().__init__(api_key, secret_key)
        self.base_url = "https://api.binance.com"
    
    def get_price(self, symbol: str) -> Decimal:
        """Get current price in USD"""
        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            params = {'symbol': f'{symbol}USDT'}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            price = data['price']
            
            return Decimal(str(price))
            
        except (requests.RequestException, KeyError, ValueError) as e:
            raise Exception(f"Failed to fetch price for {symbol}: {str(e)}")
    
    def buy_crypto(self, symbol: str, amount: Decimal) -> Dict:
        """Buy cryptocurrency (requires authenticated API)"""
        # This would require implementing Binance's signed API calls
        # with proper authentication and signature
        raise NotImplementedError("Requires Binance API authentication")
    
    def sell_crypto(self, symbol: str, amount: Decimal) -> Dict:
        """Sell cryptocurrency (requires authenticated API)"""
        # This would require implementing Binance's signed API calls
        # with proper authentication and signature
        raise NotImplementedError("Requires Binance API authentication")


def get_exchange_client(exchange_name: str, **kwargs) -> BaseCryptoExchange:
    """Factory function to get exchange client"""
    
    exchanges = {
        'coingecko': CoinGeckoAPI,
        'binance': BinanceAPI,
    }
    
    if exchange_name.lower() not in exchanges:
        raise ValueError(f"Unsupported exchange: {exchange_name}")
    
    return exchanges[exchange_name.lower()](**kwargs)
