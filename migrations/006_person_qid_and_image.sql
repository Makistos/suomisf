-- Migration 006: Add qid to person; create personimage table
--
-- 1. Add nullable text qid column to person
ALTER TABLE suomisf.person ADD COLUMN IF NOT EXISTS qid TEXT;
-- Convert to TEXT if column already existed as INTEGER
ALTER TABLE suomisf.person ALTER COLUMN qid TYPE TEXT
    USING qid::TEXT;

-- 2. Create personimage table
CREATE TABLE IF NOT EXISTS suomisf.personimage (
    id          SERIAL PRIMARY KEY,
    person_id   INTEGER NOT NULL
                    REFERENCES suomisf.person(id) ON DELETE CASCADE,
    src         TEXT NOT NULL,
    attr        TEXT,
    license     TEXT
);
-- Convert columns to TEXT if table already existed
ALTER TABLE suomisf.personimage
    ALTER COLUMN src TYPE TEXT,
    ALTER COLUMN attr TYPE TEXT,
    ALTER COLUMN license TYPE TEXT;
CREATE INDEX IF NOT EXISTS personimage_person_id_idx
    ON suomisf.personimage (person_id);
