-- Migration 023: Antikvaari per-copy exclusions and product page tracking
--
-- antikvaari_excluded_book: stores book copy IDs the user has chosen to
-- exclude from price saving. Checked at fetch time so excluded copies
-- appear pre-unchecked in the UI.
--
-- antikvaari_work_product.page_exists: tracks whether the Antikvaari
-- product page still resolves. Set to false when a fetch 404s.

CREATE TABLE suomisf.antikvaari_excluded_book (
    antikvaari_book_id VARCHAR(30) PRIMARY KEY
);

ALTER TABLE suomisf.antikvaari_work_product
    ADD COLUMN page_exists BOOLEAN NOT NULL DEFAULT TRUE;
