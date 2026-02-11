-- =============================================================================
-- Add Credits to User Account
-- =============================================================================
-- Purpose: Add testing credits to user account
-- User ID: b9b53e8a-64d0-41f7-81d5-6c53aa8325cb
-- Amount: 50 credits
-- =============================================================================

-- Start transaction
BEGIN;

-- Check current balance (before)
SELECT
  'BEFORE:' AS status,
  user_id,
  balance,
  updated_at
FROM user_credits
WHERE user_id = 'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb';

-- Create user_credits row if it doesn't exist
INSERT INTO user_credits (id, user_id, balance, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb',
  0,
  NOW(),
  NOW()
)
ON CONFLICT (user_id) DO NOTHING;

-- Add credits using stored procedure (if it exists)
-- Comment this out if the stored procedure doesn't exist
DO $$
BEGIN
  -- Try to call the stored procedure
  PERFORM credit_user_balance(
    'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb'::uuid,
    50,
    'grant',
    NULL,
    'Admin grant for testing (50 credits)'
  );
EXCEPTION
  WHEN undefined_function THEN
    -- Stored procedure doesn't exist, use manual method
    RAISE NOTICE 'Stored procedure not found, using manual method...';

    -- Update balance directly
    UPDATE user_credits
    SET balance = balance + 50,
        updated_at = NOW()
    WHERE user_id = 'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb';

    -- Log transaction
    INSERT INTO credit_transactions (id, user_id, amount, type, description, metadata, created_at)
    VALUES (
      gen_random_uuid(),
      'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb',
      50,
      'grant',
      'Admin grant for testing (50 credits)',
      '{"source": "manual_sql_script"}'::jsonb,
      NOW()
    );
END$$;

-- Check new balance (after)
SELECT
  'AFTER:' AS status,
  user_id,
  balance,
  updated_at
FROM user_credits
WHERE user_id = 'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb';

-- Show recent transaction
SELECT
  'TRANSACTION:' AS status,
  id,
  amount,
  type,
  description,
  created_at
FROM credit_transactions
WHERE user_id = 'b9b53e8a-64d0-41f7-81d5-6c53aa8325cb'
ORDER BY created_at DESC
LIMIT 5;

-- Commit transaction
COMMIT;

-- Summary
\echo '✅ Credits added successfully!'
\echo 'Run the following to verify:'
\echo 'SELECT balance FROM user_credits WHERE user_id = ''b9b53e8a-64d0-41f7-81d5-6c53aa8325cb'';'
