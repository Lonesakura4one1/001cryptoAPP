from django.urls import path
from . import views

urlpatterns = [
    # Trading pairs
    path('pairs/', views.get_trading_pairs, name='get_trading_pairs'),
    
    # Order management
    path('orders/', views.place_order, name='place_order'),
    path('orders/', views.get_orders, name='get_orders'),
    path('orders/<uuid:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Trades
    path('trades/', views.get_trades, name='get_trades'),
    
    # Market data
    path('orderbook/<str:symbol>/', views.get_order_book, name='get_order_book'),
    path('market/<str:symbol>/', views.get_market_data, name='get_market_data'),
    
    # Account
    path('account/', views.get_trading_account, name='get_trading_account'),
]
