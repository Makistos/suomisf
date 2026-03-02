-- Migration 004: Edition–Work Direct Link
-- Adds work_id directly to the edition table, eliminating the
-- Part-table indirection for the Work↔Edition relationship.
--
-- Every edition has exactly one work. Part rows with
-- shortstory_id IS NULL encoded this link redundantly; they
-- remain until Phase 5 cleanup.
--
-- Safe to re-run: column creation is guarded by a DO block.

SET search_path TO suomisf;

-- ---------------------------------------------------------------
-- 1. Add nullable work_id column (guard against re-run)
-- ---------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'suomisf'
          AND table_name   = 'edition'
          AND column_name  = 'work_id'
    ) THEN
        ALTER TABLE edition
            ADD COLUMN work_id INTEGER REFERENCES work(id);
    END IF;
END;
$$;

-- ---------------------------------------------------------------
-- 2. Populate work_id from Part where shortstory_id IS NULL
-- ---------------------------------------------------------------

UPDATE edition e
SET work_id = (
    SELECT p.work_id
    FROM part p
    WHERE p.edition_id = e.id
      AND p.work_id IS NOT NULL
      AND p.shortstory_id IS NULL
    LIMIT 1
)
WHERE e.work_id IS NULL;

-- ---------------------------------------------------------------
-- 3. Index for FK lookups
-- ---------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_edition_work_id
    ON edition(work_id);

-- ---------------------------------------------------------------
-- 5. Grant privileges
-- ---------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE
    ON suomisf.edition TO mep;

-- ---------------------------------------------------------------
-- Phase 5 cleanup (run after all tests pass):
-- Remove the Part rows whose sole purpose was the work–edition
-- link (shortstory_id IS NULL). Short-story Part rows stay.
-- Also drop the now-redundant work_id column from Part.
-- ---------------------------------------------------------------
-- DELETE FROM part WHERE shortstory_id IS NULL;
-- ALTER TABLE part DROP COLUMN IF EXISTS work_id;
