-- Migration 029: Award import source mapping
--
-- Stores, per award, which ISFDB award-category pages to scrape when
-- importing winners, plus how to interpret each one. Used by the
-- per-award "import winners from ISFDB" workflow.
--
--   isfdb_category_id : ISFDB award_category.cgi id to fetch
--   item_type         : 0 = Work, 1 = Short story, 2 = Both (novella).
--                       Determines which local table(s) a winner is
--                       matched against. NOTE: this is the scraper's
--                       item-type convention, NOT awardcategory.type.
--   our_category      : local award category name (from the canonical
--                       category map). Resolved to awardcategory.id by
--                       category type at import time, because the same
--                       name exists for both works (type 1) and short
--                       stories (type 2). NULL means unmapped.

CREATE TABLE IF NOT EXISTS suomisf.award_import_source (
    id                SERIAL PRIMARY KEY,
    award_id          INTEGER  NOT NULL
        REFERENCES suomisf.award(id) ON DELETE CASCADE,
    isfdb_category_id INTEGER  NOT NULL,
    item_type         SMALLINT NOT NULL,
    our_category      VARCHAR(50),
    UNIQUE (award_id, isfdb_category_id)
);

CREATE INDEX IF NOT EXISTS ix_award_import_source_award_id
    ON suomisf.award_import_source (award_id);
