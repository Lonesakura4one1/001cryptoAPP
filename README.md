# 001cryptoAPP - Cleo Trading Platform

An industry-standard cryptocurrency trading platform built with Django REST Framework, featuring advanced security, HD wallets, multi-signature support, and real-time trading engine.

## Features

### 🔐 Security & Authentication
- **OAuth 2.0 + OpenID Connect** for secure authentication
- **TOTP 2FA** with backup codes and QR code generation
- **Enhanced User Model** with security logging and session tracking
- **JWT Authentication** with refresh tokens

### 💼 Wallet Management
- **HD Wallets** with BIP32/BIP39 support
- **Multi-signature Wallets** with m-of-n schemes
- **Cold Storage** support with audit trails
- **Address Generation** for multiple address types (P2PKH, P2SH, Bech32)
- **Encrypted Backups** with multiple backup methods

### 📊 Trading Engine
- **Central Limit Order Book (CLOB)** with real-time matching
- **Multiple Order Types**: Market, Limit, Stop, Stop-Limit, Iceberg, TWAP
- **Order Management** with cancellation and modification
- **Trade History** with detailed execution data
- **Real-time Market Data** via WebSockets

### 🛡️ Compliance & KYC
- **KYC Verification** with document upload and OCR
- **AML Transaction Monitoring** with risk scoring
- **Compliance Rules Engine** with automated alerts
- **Regulatory Reporting** (SAR, CTR)
- **Transaction Limits** based on verification levels

### 📈 Market Data
- **Real-time Price Feeds** from multiple exchanges
- **Order Book Snapshots** with sequence numbers
- **Market Statistics** (24h volume, high/low, price changes)
- **WebSocket Streams** for live updates

### 🧪 Testing & Documentation
- **Comprehensive Test Suite** with unit and integration tests
- **API Documentation** with OpenAPI/Swagger
- **WebSocket Testing** for real-time features
- **Compliance Testing** for AML/KYC workflows

## Architecture

### Backend Stack
- **Django 6.0** - Web framework
- **Django REST Framework** - API framework
- **Channels** - WebSocket support
- **Redis** - Caching and session management
- **SQLite** - Database (development)

### Security Features
- **OAuth2 Provider** - django-oauth-toolkit
- **2FA** - pyotp + qrcode
- **Cryptography** - wallet encryption and signing
- **Security Middleware** - logging and monitoring

### Trading Infrastructure
- **Order Book Engine** - Custom CLOB implementation
- **Price Feeds** - External API integration
- **WebSocket Consumers** - Real-time data streams
- **Compliance Engine** - Automated risk assessment

## API Endpoints

### Authentication
- `POST /api/auth/login/` - JWT login
- `POST /api/auth/refresh/` - Refresh token

### Users
- `POST /api/users/register/` - User registration
- `POST /api/users/2fa/setup/` - Setup 2FA
- `GET /api/users/2fa/status/` - 2FA status

### Wallet
- `GET /api/wallet/` - Wallet details
- `POST /api/wallet/setup/hd/` - Setup HD wallet
- `POST /api/wallet/setup/multisig/` - Setup multi-sig
- `POST /api/wallet/generate-address/` - Generate address
- `GET /api/wallet/addresses/` - List addresses
- `POST /api/wallet/deposit/` - Deposit funds
- `POST /api/wallet/withdraw/` - Withdraw funds

### Trading
- `GET /api/trading/pairs/` - Trading pairs
- `POST /api/trading/orders/` - Place order
- `GET /api/trading/orders/` - User orders
- `POST /api/trading/orders/{id}/cancel/` - Cancel order
- `GET /api/trading/trades/` - User trades
- `GET /api/trading/orderbook/{symbol}/` - Order book
- `GET /api/trading/market/{symbol}/` - Market data

### Compliance
- `POST /api/compliance/kyc/profile/` - Submit KYC
- `GET /api/compliance/kyc/status/` - KYC status
- `GET /api/compliance/alerts/` - Compliance alerts
- `POST /api/compliance/check-transaction/` - Transaction check

### External Transactions
- `GET /api/transactions/prices/` - Crypto prices
- `POST /api/transactions/buy/` - Buy crypto
- `POST /api/transactions/sell/` - Sell crypto
- `GET /api/transactions/history/` - Transaction history

## WebSocket Endpoints

- `ws://localhost:8000/ws/market/` - Market data stream
- `ws://localhost:8000/ws/orderbook/` - Order book updates
- `ws://localhost:8000/ws/trading/` - User trading updates

## Setup & Installation

### Prerequisites
- Python 3.8+
- Redis server
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd cleo
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup Redis**
```bash
# On Ubuntu/Debian
sudo apt-get install redis-server

# On macOS
brew install redis

# Start Redis
redis-server
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run development server**
```bash
python manage.py runserver
```

### Running with ASGI (for WebSockets)

```bash
daphne backend.asgi:application -b 0.0.0.0 -p 8000
```

## Testing

### Run all tests
```bash
python manage.py test
```

### Run specific test modules
```bash
python manage.py test backend.tests.test_wallet
python manage.py test backend.tests.test_trading
python manage.py test backend.tests.test_compliance
python manage.py test backend.tests.test_api
```

### Run with coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## API Documentation

### Swagger UI
- **Development**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`

### Authentication
All API endpoints (except registration and login) require JWT authentication:
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl -X GET http://localhost:8000/api/wallet/ \
  -H "Authorization: Bearer <access_token>"
```

## Configuration

### Environment Variables
```bash
# Security
SECRET_KEY=your-secret-key
DEBUG=False

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Redis
REDIS_URL=redis://localhost:6379/0

# OAuth2
OAUTH2_CLIENT_ID=your-client-id
OAUTH2_CLIENT_SECRET=your-client-secret
```

### Trading Pairs
Create trading pairs via Django admin:
```python
from backend.trading.models import TradingPair

TradingPair.objects.create(
    base_currency='BTC',
    quote_currency='USD',
    symbol='BTC-USD',
    min_order_size=Decimal('0.001'),
    max_order_size=Decimal('100'),
    maker_fee=Decimal('0.0010'),
    taker_fee=Decimal('0.0010')
)
```

## Security Considerations

### Key Security Features
1. **Encryption**: All wallet seeds and private keys are encrypted
2. **2FA**: Time-based OTP with backup codes
3. **Compliance**: Automated AML/KYC checks
4. **Audit Logging**: All security events are logged
5. **Session Management**: Secure session handling with Redis

### Recommended Practices
1. **Environment Variables**: Store sensitive data in environment variables
2. **HTTPS**: Use HTTPS in production
3. **Rate Limiting**: Implement rate limiting on public endpoints
4. **Monitoring**: Set up monitoring for security events
5. **Backups**: Regular encrypted backups of critical data

## Development

### Project Structure
```
backend/
├── users/           # User management & authentication
├── wallet/          # Wallet operations & crypto utils
├── trading/         # Trading engine & order book
├── compliance/      # KYC/AML compliance
├── transactions/    # External crypto transactions
├── websocket/       # WebSocket consumers
└── tests/           # Test suites
```

### Adding New Features
1. Create new Django app: `python manage.py startapp appname`
2. Add to `INSTALLED_APPS` in settings.py
3. Define models, views, serializers
4. Add URL patterns
5. Write tests
6. Update API documentation

## Production Deployment

### Recommended Stack
- **Web Server**: Nginx
- **WSGI Server**: Gunicorn/uWSGI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Load Balancer**: Nginx/HAProxy
- **Monitoring**: Prometheus + Grafana

### Security Hardening
1. **Firewall**: Configure firewall rules
2. **SSL/TLS**: Use valid certificates
3. **Environment**: Secure environment variables
4. **Updates**: Regular security updates
5. **Backup**: Automated encrypted backups

## Contributing

### Code Style
- Follow PEP 8
- Use type hints
- Write comprehensive tests
- Document new features

### Pull Request Process
1. Fork repository
2. Create feature branch
3. Write tests
4. Submit pull request
5. Code review
6. Merge

## License

MIT License - see LICENSE file for details

## Support

- **Documentation**: `/api/docs/`
- **Issues**: GitHub Issues
- **Email**: support@example.com

## Roadmap

### Phase 2 Features
- [ ] Mobile API endpoints
- [ ] Advanced charting
- [ ] Margin trading
- [ ] Staking support
- [ ] DeFi integration

### Phase 3 Features
- [ ] Mobile applications
- [ ] Advanced analytics
- [ ] Institutional features
- [ ] Multi-asset support
- [ ] API rate limiting

---

**Note**: This platform is designed for educational and development purposes. For production use, ensure proper security audits and compliance with local regulations.
=======
# 001cryptoAPP
Acrypto exchange platform
>>>>>>> 754025aa5f65f9b060192013049ff303ddaab29c
