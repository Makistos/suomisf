-- Migration 032: add the Andre Norton Award
--
-- SFWA's Andre Norton Award for middle-grade and young-adult science
-- fiction and fantasy. Its winners are imported from sfadb.com (By-Name
-- page, single "best YA book" category), so the name must match
-- impl_award_import.SFADB_AWARD_SLUGS / SFADB_SINGLE_CATEGORY.
-- Idempotent: safe to run on a server where it was already created.

INSERT INTO suomisf.award (name, description, domestic)
SELECT 'Andre Norton Award',
       'Yhdysvaltalainen nuorten ja lasten tieteis- ja '
       'fantasiakirjallisuuden palkinto (SFWA).',
       false
WHERE NOT EXISTS (
    SELECT 1 FROM suomisf.award a WHERE a.name = 'Andre Norton Award'
);

-- Link it to the "Paras nuortenkirja" category (looked up by name so the
-- category id need not match across databases). Idempotent.
INSERT INTO suomisf.awardcategories (award_id, category_id)
SELECT a.id, c.id
FROM suomisf.award a, suomisf.awardcategory c
WHERE a.name = 'Andre Norton Award'
  AND c.name = 'Paras nuortenkirja'
  AND NOT EXISTS (
      SELECT 1 FROM suomisf.awardcategories ac
      WHERE ac.award_id = a.id AND ac.category_id = c.id
  );
