-- Migration 020: Add URL to antikvaari_work_product
--
-- Stores the Antikvaari product page URL alongside the product ID so
-- we can scrape price data without needing to re-search for the URL.

ALTER TABLE suomisf.antikvaari_work_product
    ADD COLUMN url VARCHAR(500);
