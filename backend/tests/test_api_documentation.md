# API Test Documentation

## Overview

This document provides comprehensive documentation for the API test suite in `test_api.py`. The test suite covers all major endpoints of the crypto trading platform, ensuring proper functionality, authentication, and integration between services.

## Test Structure

The test suite is organized into 5 main test classes, each covering a specific domain of the platform:

### 1. AuthenticationAPITest
Tests user authentication and registration endpoints.

#### Methods:
- `test_user_registration()`: Tests user registration via `/api/users/register/`
- `test_user_login()`: Tests JWT token generation via `/api/auth/login/`

#### Test Data:
```python
self.user_data = {
    'email': 'test@example.com',
    'password': 'testpass123',
    'username': 'testuser'
}
```

#### Expected Behaviors:
- Registration returns HTTP 201 with success message
- Login returns HTTP 200 with `access` and `refresh` tokens

### 2. WalletAPITest
Tests wallet operations and transaction management.

#### Methods:
- `test_wallet_detail()`: Tests wallet balance retrieval via `/api/wallet/`
- `test_deposit_transaction()`: Tests deposit creation via `/api/wallet/deposit/`
- `test_withdraw_transaction()`: Tests withdrawal via `/api/wallet/withdraw/`
- `test_transaction_history()`: Tests transaction listing via `/api/wallet/transactions/`

#### Test Data:
```python
deposit_data = {
    'amount': '100.00',
    'idempotency_key': 'test-deposit-123'
}

withdraw_data = {
    'amount': '50.00',
    'idempotency_key': 'test-withdraw-123'
}
```

#### Expected Behaviors:
- All operations return appropriate HTTP status codes
- Responses contain expected data fields (`balance`, `message`, `transactions`)
- Idempotency keys prevent duplicate transactions

### 3. TradingAPITest
Tests trading engine functionality and order management.

#### Methods:
- `test_get_trading_pairs()`: Tests trading pair listing via `/api/trading/pairs/`
- `test_place_order()`: Tests order placement via `/api/trading/orders/`
- `test_get_orders()`: Tests user order history via `/api/trading/orders/`
- `test_get_trades()`: Tests trade history via `/api/trading/trades/`
- `test_get_order_book()`: Tests order book data via `/api/trading/orderbook/{symbol}/`

#### Test Data:
```python
order_data = {
    'trading_pair': 'BTC-USD',
    'side': 'buy',
    'size': '1.0',
    'order_type': 'limit',
    'price': '50000.00'
}

trading_pair = TradingPair.objects.create(
    base_currency='BTC',
    quote_currency='USD',
    symbol='BTC-USD',
    min_order_size=Decimal('0.001'),
    max_order_size=Decimal('100')
)
```

#### Expected Behaviors:
- Trading pairs return as list
- Order placement returns HTTP 201 with order details
- Order book contains `bids` and `asks` arrays
- All trading operations require authentication

### 4. ComplianceAPITest
Tests KYC/AML compliance endpoints.

#### Methods:
- `test_submit_kyc_profile()`: Tests KYC profile submission via `/api/compliance/kyc/profile/`
- `test_get_kyc_status()`: Tests KYC status retrieval via `/api/compliance/kyc/status/`
- `test_get_compliance_alerts()`: Tests compliance alerts via `/api/compliance/alerts/`

#### Test Data:
```python
kyc_data = {
    'first_name': 'John',
    'last_name': 'Doe',
    'date_of_birth': '1990-01-01',
    'nationality': 'US',
    'country_of_residence': 'US',
    'address_line_1': '123 Main St',
    'city': 'New York',
    'state_province': 'NY',
    'postal_code': '10001',
    'phone_number': '+1234567890'
}
```

#### Expected Behaviors:
- KYC submission returns HTTP 201 with success message
- Status endpoint returns verification level and limits
- Alerts return as list (empty for new users)

### 5. TwoFactorAPITest
Tests two-factor authentication functionality.

#### Methods:
- `test_setup_2fa()`: Tests 2FA setup via `/api/users/2fa/setup/`
- `test_get_2fa_status()`: Tests 2FA status via `/api/users/2fa/status/`

#### Expected Behaviors:
- 2FA setup returns `secret`, `qr_code`, and `backup_codes`
- Status endpoint returns `enabled` and `setup_complete` flags

### 6. IntegrationTest
Tests complete end-to-end workflows.

#### Methods:
- `test_complete_trading_workflow()`: Tests full user journey from setup to trading

#### Workflow Steps:
1. Setup 2FA
2. Submit KYC profile
3. Setup HD wallet
4. Deposit funds
5. Place trading order
6. Verify order placement

#### Expected Behaviors:
- All steps complete successfully
- Each operation returns appropriate HTTP status
- Final state shows one active order

## Testing Patterns

### Authentication Setup
All test classes (except AuthenticationAPITest) use the same pattern for authenticated requests:

```python
def setUp(self):
    self.client = APIClient()
    self.user = User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        username='testuser'
    )
    self.client.force_authenticate(user=self.user)
```

### Common Assertions
- Status code verification: `self.assertEqual(response.status_code, status.HTTP_XXX)`
- Response data validation: `self.assertIn('field', response.data)`
- Type checking: `self.assertIsInstance(response.data, list)`

### Data Format
All test data uses strings for numeric values to match API expectations:
- Amounts: `'100.00'` (not `100.00`)
- Prices: `'50000.00'` (not `50000.00`)
- Sizes: `'1.0'` (not `1.0`)

## Error Handling

### Common Test Failures
1. **Authentication Required**: Tests may fail if endpoints require authentication
2. **Missing Dependencies**: Trading tests require TradingPair objects
3. **Data Validation**: API may reject malformed request data
4. **Database Constraints**: Unique constraint violations in test setup

### Debugging Tips
- Check response.data for detailed error messages
- Verify test data matches API schema
- Ensure proper test database isolation
- Use `--keepdb` flag for debugging test database state

## Running Tests

### Individual Test Classes
```bash
# Run specific test class
python manage.py test backend.tests.test_api.AuthenticationAPITest

# Run specific test method
python manage.py test backend.tests.test_api.AuthenticationAPITest.test_user_registration
```

### All API Tests
```bash
python manage.py test backend.tests.test_api
```

### With Verbose Output
```bash
python manage.py test backend.tests.test_api --verbosity=2
```

## Test Coverage

### Endpoints Covered
- ✅ User registration and login
- ✅ Wallet operations (CRUD)
- ✅ Trading functionality (orders, trades, order book)
- ✅ Compliance (KYC, AML, alerts)
- ✅ Two-factor authentication
- ✅ Integration workflows

### Scenarios Tested
- ✅ Happy path operations
- ✅ Authentication requirements
- ✅ Data validation
- ✅ End-to-end workflows
- ⚠️ Error scenarios (limited coverage)

## Best Practices

### Test Data Management
- Use descriptive test data
- Isolate test data between tests
- Clean up created objects when needed
- Use factories for complex object creation

### Assertion Strategy
- Test both status codes and response data
- Verify specific fields exist in responses
- Check data types match expectations
- Use parameterized tests for similar scenarios

### Maintainability
- Keep test methods focused on single scenarios
- Use descriptive test method names
- Document complex test scenarios
- Regular test suite reviews and updates

## Future Enhancements

### Additional Test Coverage
- Error scenario testing (400, 401, 403, 404 responses)
- Edge case testing (boundary values, invalid data)
- Performance testing (load, stress testing)
- Security testing (injection, authentication bypass)

### Test Utilities
- Custom test utilities for common operations
- Test data factories for complex objects
- Mock external API dependencies
- Automated test data cleanup

### Continuous Integration
- Automated test execution on code changes
- Coverage reporting and thresholds
- Performance regression detection
- Security vulnerability scanning

This documentation provides a comprehensive understanding of the API test suite and serves as a guide for maintaining and extending the test coverage.
