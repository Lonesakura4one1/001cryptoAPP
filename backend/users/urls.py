from django.urls import path
from .views import UserRegisterView
from . import views_2fa

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    
    # 2FA endpoints
    path('2fa/setup/', views_2fa.setup_2fa, name='setup_2fa'),
    path('2fa/verify-setup/', views_2fa.verify_2fa_setup, name='verify_2fa_setup'),
    path('2fa/verify/', views_2fa.verify_2fa_token, name='verify_2fa_token'),
    path('2fa/disable/', views_2fa.disable_2fa, name='disable_2fa'),
    path('2fa/status/', views_2fa.get_2fa_status, name='get_2fa_status'),
    path('2fa/regenerate-backup-codes/', views_2fa.regenerate_backup_codes, name='regenerate_backup_codes'),
]
