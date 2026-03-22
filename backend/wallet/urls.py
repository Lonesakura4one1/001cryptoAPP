from django.urls import path
from . import views
from . import views_enhanced

urlpatterns = [
    # Portfolio endpoints
    path('portfolio/', views.get_portfolio, name='get_portfolio'),    # GET /api/wallet/portfolio/
    path('portfolio-enhanced/', views.get_portfolio_enhanced, name='get_portfolio_enhanced'),  # GET /api/wallet/portfolio-enhanced/
    
    # Original wallet endpoints
    path('', views.wallet_detail, name='wallet_detail'),                # GET /api/wallet/
    path('deposit/', views.deposit, name='deposit'),              # POST /api/wallet/deposit/
    path('withdraw/', views.withdraw, name='withdraw'),            # POST /api/wallet/withdraw/
    path('transactions/', views.transaction_history, name='transaction_history'),  # GET /api/wallet/transactions/
    
    # Enhanced wallet endpoints
    path('setup/hd/', views_enhanced.setup_hd_wallet, name='setup_hd_wallet'),
    path('setup/multisig/', views_enhanced.setup_multisig_wallet, name='setup_multisig_wallet'),
    path('generate-address/', views_enhanced.generate_address, name='generate_address'),
    path('addresses/', views_enhanced.get_wallet_addresses, name='get_wallet_addresses'),
    path('backup/', views_enhanced.backup_wallet, name='backup_wallet'),
    path('cold-storage/', views_enhanced.setup_cold_storage, name='setup_cold_storage'),
]
