-- Migration 005: Drop Part Table
-- The Part table served two purposes, both now superseded:
--   1. Work↔Edition links (shortstory_id IS NULL) → edition.work_id
--      (Migration 004)
--   2. Edition↔ShortStory links (shortstory_id IS NOT NULL) →
--      editionshortstory (Migration 001)
-- Contributors were migrated to storycontributor, editioncontributor,
-- and workcontributor in Migrations 001–003.

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

DROP TABLE IF EXISTS suomisf.contributor CASCADE;
DROP TABLE IF EXISTS suomisf.part CASCADE;
