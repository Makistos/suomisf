-- Migration 005: Drop Part Table
-- The Part table served two purposes, both now superseded:
--   1. Work↔Edition links (shortstory_id IS NULL) → edition.work_id
--      (Migration 004)
--   2. Edition↔ShortStory links (shortstory_id IS NOT NULL) →
--      editionshortstory (Migration 001)
-- Contributors were migrated to storycontributor, editioncontributor,
-- and workcontributor in Migrations 001–003.
--
-- Steps:
--   1. Replace work_shortstory VIEW to use edition.work_id directly
--   2. Delete remaining Contributor rows linked to Part (Phase 4
--      cleanup for Migrations 002 and 003)
--   3. Drop Part table

SET search_path TO suomisf;

-- ---------------------------------------------------------------
-- 1. Replace work_shortstory VIEW
--    Old: JOIN part p ON p.edition_id = ess.edition_id
--          WHERE p.work_id IS NOT NULL AND p.shortstory_id IS NULL
--    New: JOIN edition e ON e.id = ess.edition_id
--          WHERE e.work_id IS NOT NULL
--    Drop first to avoid type-mismatch when column types differ.
-- ---------------------------------------------------------------

DROP VIEW IF EXISTS suomisf.work_shortstory;

CREATE VIEW suomisf.work_shortstory AS
SELECT
    e.work_id,
    ess.shortstory_id,
    MIN(ess.order_num) AS order_num
FROM suomisf.editionshortstory ess
JOIN suomisf.edition e ON e.id = ess.edition_id
WHERE e.work_id IS NOT NULL
GROUP BY e.work_id, ess.shortstory_id;

-- ---------------------------------------------------------------
-- 2. Drop Contributor and Part tables (if still present)
--    Contributor was the old generic contributor table linked via
--    part_id FK. Both tables are superseded by the specific
--    storycontributor, editioncontributor, and workcontributor
--    tables created in Migrations 001-003.
-- ---------------------------------------------------------------

DROP TABLE IF EXISTS contributor CASCADE;
DROP TABLE IF EXISTS part CASCADE;
