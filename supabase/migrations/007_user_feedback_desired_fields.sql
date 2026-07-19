ALTER TABLE user_feedback
ADD COLUMN IF NOT EXISTS desired_feedback TEXT,
ADD COLUMN IF NOT EXISTS desired_features TEXT;
