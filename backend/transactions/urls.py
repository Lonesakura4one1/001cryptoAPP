from django.urls import path
from .views import (
    get_crypto_price,
    list_crypto_prices,
    buy_crypto,
    sell_crypto,
    external_transaction_history,
    public_prices
)

urlpatterns = [
    path('public/prices/', public_prices),          # GET /api/transactions/public/prices/
    path('price/<str:symbol>/', get_crypto_price),  # GET /api/transactions/price/BTC/
    path('prices/', list_crypto_prices),            # GET /api/transactions/prices/
    path('buy/', buy_crypto),                       # POST /api/transactions/buy/
    path('sell/', sell_crypto),                     # POST /api/transactions/sell/
    path('history/', external_transaction_history), # GET /api/transactions/history/
]
