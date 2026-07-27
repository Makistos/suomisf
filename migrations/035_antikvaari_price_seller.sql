-- 035_antikvaari_price_seller.sql
--
-- Record which seller (marketplace vendor) a scraped price came from. Both
-- Antikvaari (preSelectedProduct.ynimi) and Antikka (product "Myyjä") expose
-- the seller per copy; Antikka additionally links to a vendor page (seller_url).

BEGIN;

ALTER TABLE suomisf.antikvaari_price
    ADD COLUMN IF NOT EXISTS seller TEXT;

ALTER TABLE suomisf.antikvaari_price
    ADD COLUMN IF NOT EXISTS seller_url TEXT;

COMMIT;
