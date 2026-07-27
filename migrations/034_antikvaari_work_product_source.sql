-- 034_antikvaari_work_product_source.sql
--
-- Make work<->product links source-aware so that a work can be linked to
-- products/listings from several price sources (Antikvaari, Antikka, ...).
--
-- Adds antikvaari_work_product.source_id (FK -> price_source), backfills all
-- existing rows to Antikvaari, and widens the per-work uniqueness constraint to
-- include the source.

BEGIN;

-- 1. Add the column (nullable first so the backfill can run).
ALTER TABLE suomisf.antikvaari_work_product
    ADD COLUMN IF NOT EXISTS source_id INTEGER
        REFERENCES suomisf.price_source(id);

-- 2. Backfill existing links to the Antikvaari source.
UPDATE suomisf.antikvaari_work_product
    SET source_id = (SELECT id FROM suomisf.price_source WHERE name = 'Antikvaari')
    WHERE source_id IS NULL;

-- 3. Enforce NOT NULL now that every row has a source.
ALTER TABLE suomisf.antikvaari_work_product
    ALTER COLUMN source_id SET NOT NULL;

-- 4. Replace the (work_id, product_id) uniqueness with a source-scoped one.
ALTER TABLE suomisf.antikvaari_work_product
    DROP CONSTRAINT IF EXISTS antikvaari_work_product_work_id_antikvaari_product_id_key;

ALTER TABLE suomisf.antikvaari_work_product
    ADD CONSTRAINT antikvaari_work_product_work_source_product_key
        UNIQUE (work_id, source_id, antikvaari_product_id);

CREATE INDEX IF NOT EXISTS ix_antikvaari_work_product_source_id
    ON suomisf.antikvaari_work_product (source_id);

COMMIT;
