# Crypto Trading Platform Backend - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Configuration Files](#core-configuration-files)
4. [Module-by-Module Analysis](#module-by-module-analysis)
5. [API Endpoints](#api-endpoints)
6. [Database Schema](#database-schema)
7. [Security Features](#security-features)
8. [Background Tasks & Celery](#background-tasks--celery)
9. [WebSocket Implementation](#websocket-implementation)
10. [Dependencies & Requirements](#dependencies--requirements)

## Overview

The Crypto Trading Platform is a comprehensive Django-based backend system designed for cryptocurrency trading with advanced security, compliance, and wallet management features. The platform implements industry-standard practices for digital asset exchanges.

### Key Features Implemented
- **User Management**: Enhanced user model with 2FA, security logging, and session tracking
- **Wallet System**: HD wallets, multi-signature support, cold storage management
- **Trading Engine**: Order matching, market data, and trading account management
- **Compliance & KYC**: AML monitoring, document verification, regulatory reporting
- **Transaction Processing**: Deposit/withdrawal handling with blockchain integration
- **Real-time Communication**: WebSocket support for live market data
- **Background Processing**: Celery-based task queue for price updates and compliance checks

## Architecture

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Mobile App    │    │   External      │
│   (React)       │    │   (React Native)│    │   APIs          │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      Django Backend      │
                    │   (REST API + WebSocket) │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
    ┌─────┴─────┐        ┌───────┴───────┐      ┌───────┴───────┐
    │   Redis    │        │ PostgreSQL    │      │   Celery      │
    │ (Cache/WS) │        │  (Database)   │      │ (Tasks)       │
    └────────────┘        └───────────────┘      └───────────────┘
```

### Technology Stack
- **Framework**: Django 6.0 with Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Cache/Messaging**: Redis
- **Background Tasks**: Celery
- **WebSocket**: Django Channels
- **Authentication**: JWT + OAuth2 + 2FA
- **Crypto Libraries**: bitcoinlib, ecdsa, mnemonic

## Core Configuration Files

### settings.py
**Purpose**: Main Django configuration with security, database, and app settings

**Key Components**:
```python
# Custom user model
AUTH_USER_MODEL = 'users.User'

# Installed apps include core modules
INSTALLED_APPS = [
    'django.contrib.admin',
    'rest_framework',
    'corsheaders',
    'oauth2_provider',
    'backend.users',
    'backend.wallet',
    'backend.transactions',
    'backend.compliance',
    'backend.trading',
]

# Security middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'backend.users.middleware.SecurityMiddleware',
]

# JWT authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# Redis caching and sessions
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Channels for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [('127.0.0.1', 6379)]},
    },
}
```

### urls.py
**Purpose**: Main URL routing configuration

**URL Structure**:
- `/admin/` - Django admin
- `/api/docs/` - Swagger documentation
- `/api/auth/` - JWT authentication endpoints
- `/api/users/` - User management and 2FA
- `/api/wallet/` - Wallet operations
- `/api/transactions/` - External crypto transactions
- `/api/compliance/` - KYC and AML compliance
- `/api/trading/` - Trading engine

### asgi.py
**Purpose**: ASGI configuration for HTTP and WebSocket protocols

**Key Features**:
- Protocol type routing for HTTP and WebSocket
- Authentication middleware for WebSocket connections
- Environment-based settings loading

### celery.py
**Purpose**: Celery configuration for background tasks

**Scheduled Tasks**:
- `update-crypto-prices` (every 1 minute)
- `process-aml-checks` (every 5 minutes)
- `cleanup-sessions` (every hour)
- `generate-reports` (daily)

## Module-by-Module Analysis

### 1. Users Module (`backend/users/`)

**Purpose**: User authentication, authorization, and security management

#### Models:

**User Model** (`models.py`)
```python
class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    kyc_level = models.IntegerField(default=0)  # 0=none, 1=basic, 2=advanced
    risk_score = models.IntegerField(default=0)  # 0=low, 100=high risk
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
```

**TwoFactorAuth Model**
```python
class TwoFactorAuth(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    secret_key = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)
    
    def generate_secret(self):
        self.secret_key = pyotp.random_base32()
        self.save()
        return self.secret_key
    
    def verify_token(self, token):
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)
```

**UserSession Model**
- Tracks active user sessions for security monitoring
- Stores IP address, user agent, and activity timestamps

**SecurityLog Model**
- Logs security events (login, 2FA changes, KYC updates)
- Supports audit trails and compliance reporting

#### Views:
- `views_2fa.py` - Two-factor authentication endpoints
- Registration, login, and profile management
- Session management and security logging

#### Key Features:
- TOTP-based 2FA with backup codes
- QR code generation for authenticator apps
- Session tracking and security monitoring
- Risk scoring and suspicious activity detection

### 2. Wallet Module (`backend/wallet/`)

**Purpose**: Cryptocurrency wallet management with HD and multi-signature support

#### Models:

**Wallet Model** (`models.py`)
```python
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    wallet_type = models.CharField(max_length=20, choices=[
        ('hd', 'HD Wallet'),
        ('multisig', 'Multi-Signature'),
        ('simple', 'Simple Address'),
    ], default='hd')
    
    # HD Wallet fields
    mnemonic_encrypted = models.TextField(blank=True, null=True)
    seed_encrypted = models.TextField(blank=True, null=True)
    derivation_path = models.CharField(max_length=100, default="m/44'/0'/0'/0/0")
    
    # Multi-sig fields
    m_required = models.IntegerField(default=1)
    n_total = models.IntegerField(default=1)
    public_keys = models.JSONField(default=list, blank=True)
    
    # Security
    is_cold_storage = models.BooleanField(default=False)
    is_hardware_wallet = models.BooleanField(default=False)
```

**Transaction Model**
```python
class Transaction(models.Model):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    
    # Blockchain integration
    tx_hash = models.CharField(max_length=100, blank=True, null=True)
    from_address = models.CharField(max_length=100, blank=True, null=True)
    to_address = models.CharField(max_length=100, blank=True, null=True)
    confirmations = models.IntegerField(default=0)
    block_height = models.IntegerField(null=True, blank=True)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
```

**ColdStorage Model**
- Manages cold storage wallet configurations
- Tracks audit schedules and access controls

**WalletBackup Model**
- Records wallet backup operations
- Supports multiple backup types (mnemonic, private key, keystore)

#### Crypto Utilities (`crypto_utils.py`)

**HDWallet Class**
```python
class HDWallet:
    def __init__(self, seed=None):
        if seed:
            self.seed = seed
            self.master_key = self._generate_master_key(seed)
        else:
            self.seed = self._generate_seed()
            self.master_key = self._generate_master_key(self.seed)
    
    def derive_path(self, path):
        """Derive key from BIP32 path like m/44'/0'/0'/0/0"""
        current_key = self.master_key
        for part in path.split('/')[1:]:
            hardened = part.endswith("'")
            index = int(part.rstrip("'"))
            current_key = self.derive_child(current_key, index, hardened)
        return current_key
    
    def get_address(self, private_key, address_type='p2pkh'):
        """Generate Bitcoin address from private key"""
        if address_type == 'p2pkh':
            return self._p2pkh_address(private_key)
```

**MultiSigWallet Class**
- Implements multi-signature wallet functionality
- Generates redeem scripts and addresses

**CryptoUtils Class**
- Encryption/decryption for private keys
- Mnemonic phrase generation and validation
- Address generation for different address types

#### Key Features:
- BIP32 hierarchical deterministic wallets
- Multi-signature wallet support
- Cold storage and hardware wallet integration
- Encrypted backup and recovery
- Transaction monitoring and confirmation tracking

### 3. Compliance Module (`backend/compliance/`)

**Purpose**: KYC verification, AML monitoring, and regulatory compliance

#### Models:

**KYCDocument Model**
```python
class KYCDocument(models.Model):
    DOCUMENT_TYPES = [
        ('passport', 'Passport'),
        ('driver_license', 'Driver License'),
        ('national_id', 'National ID'),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('selfie', 'Selfie with Document'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    front_image = models.ImageField(upload_to='kyc/front/')
    back_image = models.ImageField(upload_to='kyc/back/', null=True, blank=True)
    selfie_image = models.ImageField(upload_to='kyc/selfie/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ], default='pending')
    
    verification_score = models.IntegerField(default=0)  # 0-100 confidence score
    extracted_data = models.JSONField(default=dict, blank=True)  # OCR extracted data
```

**KYCProfile Model**
```python
class KYCProfile(models.Model):
    VERIFICATION_LEVELS = [
        (0, 'Not Verified'),
        (1, 'Basic - Email Verified'),
        (2, 'Tier 1 - Document Verified'),
        (3, 'Tier 2 - Enhanced Verification'),
        (4, 'Tier 3 - Institutional'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    verification_level = models.IntegerField(default=0, choices=VERIFICATION_LEVELS)
    
    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=50)
    country_of_residence = models.CharField(max_length=50)
    
    # Risk assessment
    risk_score = models.IntegerField(default=0)  # 0-100 risk score
    risk_factors = models.JSONField(default=list, blank=True)
    
    # Transaction limits based on verification level
    daily_transaction_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    monthly_transaction_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    annual_transaction_limit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
```

**AMLTransaction Model**
```python
class AMLTransaction(models.Model):
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction_hash = models.CharField(max_length=100, unique=True)
    
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=10)
    from_address = models.CharField(max_length=100)
    to_address = models.CharField(max_length=100)
    
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)
    risk_score = models.IntegerField(default=0)  # 0-100
    risk_factors = models.JSONField(default=list, blank=True)
    
    # AML checks
    sanction_check = models.BooleanField(default=False)
    pep_check = models.BooleanField(default=False)
    blacklist_check = models.BooleanField(default=False)
    unusual_pattern = models.BooleanField(default=False)
```

**ComplianceReport Model**
- Generates regulatory reports (SAR, CTR, annual reports)
- Tracks submission status and regulatory body responses

**ComplianceRule Model**
- Configurable automated compliance rules
- Supports various rule types (limits, thresholds, patterns)

**ComplianceAlert Model**
- Real-time compliance alerts and notifications
- Tracks acknowledgment and resolution

#### Services (`services.py`)
**AMLService Class**
- Transaction risk analysis
- Sanctions and PEP screening
- Pattern detection and anomaly identification

**KYCService Class**
- Document verification processing
- OCR data extraction
- Identity verification workflows

#### Key Features:
- Multi-tier KYC verification
- Automated AML monitoring
- Regulatory reporting (SAR, CTR)
- Risk scoring and transaction limits
- Document OCR and verification
- Compliance rule engine

### 4. Trading Module (`backend/trading/`)

**Purpose**: Cryptocurrency trading engine with order matching and market data

#### Models:

**TradingPair Model**
```python
class TradingPair(models.Model):
    base_currency = models.CharField(max_length=10)  # BTC
    quote_currency = models.CharField(max_length=10)  # USD
    symbol = models.CharField(max_length=20, unique=True)  # BTC-USD
    
    # Trading settings
    min_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    max_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    price_precision = models.IntegerField(default=8)
    size_precision = models.IntegerField(default=8)
    
    # Fees
    maker_fee = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0010'))
    taker_fee = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.0010'))
    
    is_active = models.BooleanField(default=True)
    is_margin_trading = models.BooleanField(default=False)
```

**Order Model**
```python
class Order(models.Model):
    ORDER_TYPES = [
        ('market', 'Market Order'),
        ('limit', 'Limit Order'),
        ('stop', 'Stop Order'),
        ('stop_limit', 'Stop Limit'),
        ('iceberg', 'Iceberg Order'),
        ('twap', 'Time-Weighted Average Price'),
    ]
    
    SIDES = [('buy', 'Buy'), ('sell', 'Sell')]
    
    STATUSES = [
        ('pending', 'Pending'),
        ('open', 'Open'),
        ('filled', 'Filled'),
        ('partially_filled', 'Partially Filled'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE)
    
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    side = models.CharField(max_length=10, choices=SIDES)
    size = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    filled_size = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    average_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    time_in_force = models.CharField(max_length=3, choices=[
        ('GTC', 'Good Till Cancelled'),
        ('IOC', 'Immediate Or Cancel'),
        ('FOK', 'Fill Or Kill'),
        ('GTD', 'Good Till Date'),
    ], default='GTC')
```

**Trade Model**
```python
class Trade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    taker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='taker_trades')
    maker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='maker_trades')
    
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE)
    size = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    
    taker_fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    maker_fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
```

**OrderBook Model**
- Stores order book snapshots
- JSON-based bid/ask data storage
- Sequence numbering for consistency

**MarketData Model**
- Real-time market statistics
- Price, volume, and trading metrics
- 24-hour price changes and statistics

**TradingAccount Model**
```python
class TradingAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Account balances
    available_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    frozen_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Trading statistics
    total_trades = models.IntegerField(default=0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_fees_paid = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Risk management
    margin_used = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    margin_free = models.DecimalField(max_digits=20, decimal_places=8, default=0)
```

#### Trading Engine (`engine.py`)
**TradingEngine Class**
- Order matching algorithm
- Price-time priority execution
- Trade execution and fee calculation
- Order book management

#### Key Features:
- Multiple order types (market, limit, stop, iceberg, TWAP)
- Real-time order matching
- Market data streaming
- Trading account management
- Fee calculation and collection
- Order book depth management

### 5. Transactions Module (`backend/transactions/`)

**Purpose**: External cryptocurrency transaction processing and blockchain integration

#### Models:

**Transaction Model** (shared with wallet module)
- External deposit and withdrawal processing
- Blockchain transaction tracking
- Confirmation monitoring

#### API Clients (`api_clients.py`)
**ExchangeClient Classes**
- Integration with external exchanges (CoinGecko, etc.)
- Price fetching and market data
- Transaction broadcasting

#### Key Features:
- External API integration
- Price updates from multiple sources
- Blockchain transaction monitoring
- Deposit/withdrawal processing

### 6. Health Module (`backend/health/`)

**Purpose**: System health monitoring and status endpoints

#### Views (`views.py`)
- Health check endpoints
- System status monitoring
- Database connectivity checks
- Redis connectivity checks

#### Key Features:
- Application health monitoring
- Database status checks
- External service connectivity
- Performance metrics

### 7. WebSocket Module (`backend/websocket/`)

**Purpose**: Real-time communication for live data streaming

#### Consumers (`consumers.py`)

**MarketDataConsumer Class**
```python
class MarketDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.trading_pair = None
        
        if isinstance(self.user, AnonymousUser):
            await self.close(code=4001)
            return
        
        await self.accept()
    
    async def handle_subscribe(self, data):
        """Handle subscription requests"""
        symbol = data.get('symbol')
        channels = data.get('channels', [])
        
        # Get trading pair and join room
        trading_pair = await database_sync_to_async(
            TradingPair.objects.get
        )(symbol=symbol, is_active=True)
        
        await self.channel_layer.group_add(
            f"market_{symbol}",
            self.channel_name
        )
```

#### Routing (`routing.py`)
- WebSocket URL routing
- Channel layer configuration

#### Key Features:
- Real-time market data streaming
- Order book updates
- Trade notifications
- Live price updates
- User-specific notifications

## Background Tasks & Celery

### Task Configuration (`celery.py`)
```python
app.conf.beat_schedule = {
    'update-crypto-prices': {
        'task': 'backend.transactions.tasks.update_crypto_prices',
        'schedule': 60.0,  # Every 1 minute
    },
    'process-aml-checks': {
        'task': 'backend.compliance.tasks.process_aml_checks',
        'schedule': 300.0,  # Every 5 minutes
    },
    'cleanup-sessions': {
        'task': 'backend.users.tasks.cleanup_expired_sessions',
        'schedule': 3600.0,  # Every hour
    },
    'generate-reports': {
        'task': 'backend.compliance.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Every day at midnight
    },
}
```

### Tasks (`tasks.py`)

**Price Update Task**
```python
@shared_task
def update_crypto_prices():
    """Update cryptocurrency prices from external APIs"""
    exchange = get_exchange_client('coingecko')
    currencies = settings.CRYPTO_PLATFORM['SUPPORTED_CURRENCIES']
    
    updated_prices = {}
    for currency in currencies:
        price = exchange.get_price(currency)
        updated_prices[currency] = price
    
    cache.set('crypto_prices', updated_prices, timeout=300)
    return updated_prices
```

**AML Processing Task**
```python
@shared_task
def process_aml_checks():
    """Process AML checks for pending transactions"""
    pending_transactions = AMLTransaction.objects.filter(status='monitoring')
    
    for transaction in pending_transactions:
        aml_service = AMLService()
        result = aml_service.analyze_transaction(transaction)
        
        if result['risk_level'] in ['high', 'critical']:
            # Generate compliance alert
            pass
```

## API Endpoints

### Authentication Endpoints
- `POST /api/auth/login/` - JWT token generation
- `POST /api/auth/refresh/` - JWT token refresh

### User Management
- `POST /api/users/register/` - User registration
- `GET /api/users/profile/` - User profile
- `PUT /api/users/profile/` - Update profile
- `POST /api/users/2fa/setup/` - Setup 2FA
- `POST /api/users/2fa/verify/` - Verify 2FA token

### Wallet Operations
- `GET /api/wallet/` - Get wallet info
- `POST /api/wallet/create/` - Create new wallet
- `POST /api/wallet/generate-address/` - Generate new address
- `GET /api/wallet/transactions/` - Get transaction history
- `POST /api/wallet/withdraw/` - Initiate withdrawal

### Trading Endpoints
- `GET /api/trading/pairs/` - Get trading pairs
- `GET /api/trading/orderbook/` - Get order book
- `POST /api/trading/orders/` - Create order
- `GET /api/trading/orders/` - Get user orders
- `DELETE /api/trading/orders/{id}/` - Cancel order
- `GET /api/trading/trades/` - Get trade history

### Compliance Endpoints
- `POST /api/compliance/kyc/submit/` - Submit KYC documents
- `GET /api/compliance/kyc/status/` - Get KYC status
- `GET /api/compliance/alerts/` - Get compliance alerts

## Security Features

### Authentication & Authorization
- JWT-based authentication with refresh tokens
- OAuth2 provider integration
- Two-factor authentication (TOTP)
- Session management and tracking

### Data Protection
- Encrypted private key storage
- Redis-based session storage
- CORS configuration
- Security headers (XSS protection, content type sniffing)

### Compliance & Monitoring
- AML transaction monitoring
- KYC document verification
- Security event logging
- Risk scoring system

### Access Controls
- Role-based permissions
- API rate limiting
- IP-based restrictions
- Suspicious activity detection

## Dependencies & Requirements

### Core Framework
```
Django==6.0
djangorestframework==3.16.1
djangorestframework_simplejwt==5.5.1
django-cors-headers==4.9.0
```

### Security & Authentication
```
django-oauth-toolkit==1.7.1
pyotp==2.9.0
qrcode==7.4.2
cryptography==42.0.8
```

### Database & Caching
```
redis==5.0.1
django-redis==5.4.0
psycopg2-binary==2.9.7
```

### Background Tasks
```
celery==5.3.4
flower==2.0.1
```

### Cryptocurrency Support
```
bitcoinlib==0.6.13
ecdsa==0.18.0
mnemonic==0.20
bip32==5.0.0
```

### WebSocket Support
```
channels==4.1.0
channels-redis==4.1.0
```

### Image Processing
```
pillow==10.1.0
```

### Production & Monitoring
```
gunicorn==21.2.0
whitenoise==6.6.0
sentry-sdk==1.40.6
psutil==5.9.8
```

## Database Schema

### Core Tables
1. **users_user** - Extended user accounts
2. **users_twofactorauth** - 2FA configurations
3. **users_usersession** - Active sessions
4. **users_securitylog** - Security events

### Wallet Tables
1. **wallet_wallet** - User wallets
2. **wallet_walletaddress** - Generated addresses
3. **wallet_transaction** - Transaction records
4. **wallet_coldstorage** - Cold storage configs
5. **wallet_walletbackup** - Backup records

### Compliance Tables
1. **compliance_kycdocument** - KYC documents
2. **compliance_kycprofile** - User KYC profiles
3. **compliance_amltransaction** - AML monitoring
4. **compliance_compliancereport** - Regulatory reports
5. **compliance_compliancerule** - Compliance rules
6. **compliance_compliancealert** - Compliance alerts

### Trading Tables
1. **trading_tradingpair** - Trading pairs
2. **trading_order** - Trading orders
3. **trading_trade** - Executed trades
4. **trading_orderbook** - Order book snapshots
5. **trading_marketdata** - Market statistics
6. **trading_tradingaccount** - User trading accounts

## Key Design Patterns

### 1. Service Layer Pattern
- Business logic separated from views
- Reusable service classes (AMLService, KYCService, TradingEngine)

### 2. Repository Pattern
- Data access abstraction through models
- Custom model managers for complex queries

### 3. Factory Pattern
- Wallet creation (HD, multi-sig, simple)
- API client creation for different exchanges

### 4. Observer Pattern
- WebSocket consumers for real-time updates
- Signal handlers for model events

### 5. Strategy Pattern
- Different order types in trading engine
- Various compliance rule types

## Performance Considerations

### Database Optimization
- Indexed fields for frequent queries
- Database connection pooling
- Query optimization with select_related/prefetch_related

### Caching Strategy
- Redis for session storage
- Price data caching
- Order book snapshots caching

### Background Processing
- Asynchronous task processing
- Queue management for high-volume operations
- Scheduled tasks for maintenance

### WebSocket Performance
- Channel layer for efficient broadcasting
- Connection pooling and management
- Message compression for large data

## Scalability Features

### Horizontal Scaling
- Stateless application design
- Redis for shared state
- Database sharding support

### Load Balancing
- Multiple worker processes
- WebSocket connection distribution
- Task queue scaling

### Monitoring & Observability
- Health check endpoints
- Performance metrics collection
- Error tracking and logging

This comprehensive documentation covers all aspects of the crypto trading platform backend, including detailed code analysis, architecture patterns, and implementation details for each module.
