-- Store normalized assets mentioned in a reflection without changing reflection_notes.
CREATE TABLE IF NOT EXISTS reflection_asset_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reflection_id UUID NOT NULL REFERENCES reflection_notes(id) ON DELETE CASCADE,
    market TEXT NOT NULL DEFAULT 'unknown',
    symbol TEXT NOT NULL,
    asset_name TEXT,
    asset_type TEXT NOT NULL DEFAULT 'stock',
    source_field TEXT NOT NULL,
    matched_text TEXT NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 1.000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (reflection_id, market, symbol)
);

CREATE INDEX IF NOT EXISTS idx_asset_mentions_user_symbol
    ON reflection_asset_mentions(user_id, market, symbol);

CREATE INDEX IF NOT EXISTS idx_asset_mentions_reflection
    ON reflection_asset_mentions(reflection_id);

ALTER TABLE reflection_asset_mentions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own asset mentions" ON reflection_asset_mentions;
CREATE POLICY "Users can view own asset mentions"
    ON reflection_asset_mentions FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own asset mentions" ON reflection_asset_mentions;
CREATE POLICY "Users can insert own asset mentions"
    ON reflection_asset_mentions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own asset mentions" ON reflection_asset_mentions;
CREATE POLICY "Users can delete own asset mentions"
    ON reflection_asset_mentions FOR DELETE
    USING (auth.uid() = user_id);
