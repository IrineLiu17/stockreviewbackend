-- Migration: Auto-create user profile when user signs up
-- This trigger automatically creates a user_profiles record when a new user is created in auth.users

-- Function to handle new user creation
-- SECURITY DEFINER allows the function to bypass RLS policies
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, subscription_tier)
    VALUES (
        NEW.id,
        NEW.email,
        'free'
    )
    ON CONFLICT (id) DO NOTHING;  -- If profile already exists, do nothing
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add INSERT policy for user_profiles (if not exists)
-- This allows the trigger function to insert new profiles
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'user_profiles' 
        AND policyname = 'Users can insert own profile'
    ) THEN
        CREATE POLICY "Users can insert own profile"
            ON user_profiles FOR INSERT
            WITH CHECK (auth.uid() = id);
    END IF;
END $$;

-- Trigger to call the function when a new user is created
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Also create profile for existing users (if any)
-- This is a one-time migration for users who already exist
INSERT INTO public.user_profiles (id, email, subscription_tier)
SELECT 
    id,
    email,
    'free'
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.user_profiles)
ON CONFLICT (id) DO NOTHING;
