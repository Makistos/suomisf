-- 040_price_source_kampinkirjakauppa.sql
--
-- Register kampinkirjakauppa.fi as a price source (single independent shop,
-- Kotisivukone webstore search + product pages).

INSERT INTO suomisf.price_source (name)
VALUES ('Kampin kirjakauppa')
ON CONFLICT (name) DO NOTHING;
