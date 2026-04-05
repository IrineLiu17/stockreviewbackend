-- Migration: Add nickname field to user_profiles
-- This allows users to set a custom display name

-- Add nickname column to user_profiles table
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS nickname TEXT;

-- Add comment to explain the field
COMMENT ON COLUMN user_profiles.nickname IS 'User display name/nickname. NULL means user has not set a nickname yet.';

-- Note: RLS policies for SELECT and UPDATE already exist from 001_initial_schema.sql
-- These policies will automatically apply to the nickname field as well:
-- - "Users can view own profile" (SELECT)
-- - "Users can update own profile" (UPDATE)
-- No additional RLS policies needed for nickname field
