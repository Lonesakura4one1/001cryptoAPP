from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from .schema import info, schema_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health Check Endpoints
    path('api/', include('backend.health.urls')),

    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # JWT Authentication
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User Registration & 2FA
    path('api/users/', include('backend.users.urls')),

    # Wallet Operations
    path('api/wallet/', include('backend.wallet.urls')),
    
    # External Crypto Transactions
    path('api/transactions/', include('backend.transactions.urls')),
    
    # Compliance & KYC
    path('api/compliance/', include('backend.compliance.urls')),
    
    # Trading Engine
    path('api/trading/', include('backend.trading.urls')),
]

