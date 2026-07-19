-- 记录「请用户评分」弹窗触发次数（匿名，仅用于统计）
CREATE TABLE IF NOT EXISTS review_prompt_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT DEFAULT 'ios_app'
);

-- 允许应用（anon）插入，便于 App 触发时上报
ALTER TABLE review_prompt_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow insert for anon"
    ON review_prompt_events FOR INSERT
    WITH CHECK (true);

-- 仅查看用，可按需在 Dashboard 用 SQL 查：SELECT COUNT(*), DATE(created_at) FROM review_prompt_events GROUP BY DATE(created_at);
CREATE POLICY "Allow select for anon"
    ON review_prompt_events FOR SELECT
    USING (true);
