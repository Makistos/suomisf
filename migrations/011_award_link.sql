-- Migration 011: Add awardlink table
-- Stores external links (URLs + optional description) for awards.

CREATE TABLE IF NOT EXISTS suomisf.awardlink (
    id    SERIAL PRIMARY KEY,
    award_id INTEGER NOT NULL
        REFERENCES suomisf.award(id) ON DELETE CASCADE,
    link        TEXT NOT NULL,
    description TEXT
);
