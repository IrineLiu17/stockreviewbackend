-- User feedback survey: one-time questionnaire (helpful + improvements + other)
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    helpful BOOLEAN NOT NULL,
    improvements TEXT[] NOT NULL,
    other_feedback TEXT,
    app_version TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at DESC);

ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own feedback"
    ON user_feedback FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow select for service"
    ON user_feedback FOR SELECT
    USING (true);

-- Track whether user has submitted feedback (so we don't show modal again)
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS has_submitted_feedback BOOLEAN DEFAULT false;
