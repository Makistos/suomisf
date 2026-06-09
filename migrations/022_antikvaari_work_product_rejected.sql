-- Migration 022: Add rejected flag to antikvaari_work_product.
-- Products that appear in search results but are not linked to a work
-- are saved with rejected=true so the UI can skip them in future searches.

ALTER TABLE suomisf.antikvaari_work_product
    ADD COLUMN rejected BOOLEAN NOT NULL DEFAULT FALSE;
