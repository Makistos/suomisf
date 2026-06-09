-- Migration 004: Edition–Work Direct Link
-- Adds work_id directly to the edition table, eliminating the
-- Part-table indirection for the Work↔Edition relationship.
--
-- Safe to re-run: column creation is guarded by a DO block.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'suomisf'
          AND table_name   = 'edition'
          AND column_name  = 'work_id'
    ) THEN
        ALTER TABLE suomisf.edition
            ADD COLUMN work_id INTEGER REFERENCES suomisf.work(id);
    END IF;
END;
$$;

UPDATE suomisf.edition e
SET work_id = (
    SELECT p.work_id
    FROM suomisf.part p
    WHERE p.edition_id = e.id
      AND p.work_id IS NOT NULL
      AND p.shortstory_id IS NULL
    LIMIT 1
)
WHERE e.work_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_edition_work_id
    ON suomisf.edition(work_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.edition TO mep;
