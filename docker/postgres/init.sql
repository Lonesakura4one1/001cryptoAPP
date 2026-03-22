-- PostgreSQL initialization script for crypto platform
-- This script runs when the database container is first created

-- Create additional extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance (these will be created by Django migrations too)
-- But having them here ensures they exist from the start

-- You can add any custom database initialization here
-- For example, creating initial trading pairs:
-- INSERT INTO trading_tradingpair (base_currency, quote_currency, symbol, min_order_size, max_order_size, price_precision, size_precision, maker_fee, taker_fee, is_active, created_at, updated_at)
-- VALUES 
-- ('BTC', 'USD', 'BTC-USD', 0.0001, 100, 8, 8, 0.001, 0.001, true, NOW(), NOW()),
-- ('ETH', 'USD', 'ETH-USD', 0.001, 1000, 8, 8, 0.001, 0.001, true, NOW(), NOW());

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crypto_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crypto_user;
