-- Migration 014: Add pageview table for visitor analytics

CREATE TABLE suomisf.pageview (
    id          SERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip          VARCHAR(45) NOT NULL,
    path        VARCHAR(255) NOT NULL,
    user_agent  TEXT,
    country     VARCHAR(2),
    browser     VARCHAR(100),
    os          VARCHAR(100),
    device_type VARCHAR(20)
);

CREATE INDEX ix_pageview_created_at ON suomisf.pageview (created_at);
CREATE INDEX ix_pageview_ip         ON suomisf.pageview (ip);
CREATE INDEX ix_pageview_path       ON suomisf.pageview (path);
