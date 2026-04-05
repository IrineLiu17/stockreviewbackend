-- Migration: Fix RLS policy for reflection_notes
-- This ensures that the INSERT policy correctly checks auth.uid()

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can insert own notes" ON reflection_notes;

-- Recreate the INSERT policy with explicit check
CREATE POLICY "Users can insert own notes"
    ON reflection_notes FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

-- Also ensure SELECT policy allows users to see their own notes
DROP POLICY IF EXISTS "Users can view own notes" ON reflection_notes;

CREATE POLICY "Users can view own notes"
    ON reflection_notes FOR SELECT
    USING (auth.uid()::text = user_id::text);

-- Add a function to help debug RLS issues
CREATE OR REPLACE FUNCTION debug_auth_uid()
RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE(auth.uid()::text, 'NULL');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION debug_auth_uid() TO authenticated;
