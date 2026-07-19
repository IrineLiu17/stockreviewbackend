CREATE TABLE IF NOT EXISTS auth_analytics_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name text NOT NULL,
    session_id text,
    source text DEFAULT 'ios_app',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE auth_analytics_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anon and authenticated users can insert auth analytics events"
    ON auth_analytics_events FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_auth_analytics_events_event_name_created_at
    ON auth_analytics_events (event_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_analytics_events_session_id_created_at
    ON auth_analytics_events (session_id, created_at DESC);
