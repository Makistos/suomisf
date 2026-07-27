-- 036_widen_price_id_columns_to_text.sql
--
-- Antikka product identifiers are URL slugs that can be very long (100+ chars),
-- overflowing the VARCHAR(30)/VARCHAR(100) id columns and failing inserts when
-- linking or saving antikka listings. Widen all price id columns to TEXT.

BEGIN;

ALTER TABLE suomisf.antikvaari_work_product
    ALTER COLUMN antikvaari_product_id TYPE TEXT;

ALTER TABLE suomisf.antikvaari_excluded_book
    ALTER COLUMN antikvaari_book_id TYPE TEXT;

ALTER TABLE suomisf.antikvaari_price
    ALTER COLUMN antikvaari_product_id TYPE TEXT;

ALTER TABLE suomisf.antikvaari_price
    ALTER COLUMN antikvaari_book_id TYPE TEXT;

COMMIT;
