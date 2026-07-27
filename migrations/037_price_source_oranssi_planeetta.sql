-- 037_price_source_oranssi_planeetta.sql
--
-- Register oranssiplaneetta.fi as a price source (WooCommerce shop, same shape
-- as antikka.net).

INSERT INTO suomisf.price_source (name)
VALUES ('Oranssi Planeetta')
ON CONFLICT (name) DO NOTHING;
