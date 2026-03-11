-- Migration 006: Add qid to person; create personimage table
--
-- 1. Add nullable integer qid column to person
ALTER TABLE suomisf.person ADD COLUMN IF NOT EXISTS qid INTEGER;

-- 2. Create personimage table
CREATE TABLE IF NOT EXISTS suomisf.personimage (
    id          SERIAL PRIMARY KEY,
    person_id   INTEGER NOT NULL
                    REFERENCES suomisf.person(id) ON DELETE CASCADE,
    src         VARCHAR(200) NOT NULL,
    attr        VARCHAR(200),
    license     VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS personimage_person_id_idx
    ON suomisf.personimage (person_id);
