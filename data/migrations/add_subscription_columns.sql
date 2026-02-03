-- Stripe subscription columns for users table
-- Run: psql -d turing -f data/migrations/add_subscription_columns.sql

-- Add subscription-related columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free',
ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS subscription_period_end TIMESTAMPTZ;

-- Index for Stripe lookups
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer 
ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- Comment
COMMENT ON COLUMN users.subscription_tier IS 'Subscription tier: free, standard, sustainer';
COMMENT ON COLUMN users.subscription_status IS 'Stripe subscription status: active, past_due, canceled';
COMMENT ON COLUMN users.stripe_customer_id IS 'Stripe customer ID for billing';
COMMENT ON COLUMN users.stripe_subscription_id IS 'Active Stripe subscription ID';
COMMENT ON COLUMN users.subscription_period_end IS 'End of current billing period';
