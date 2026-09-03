-- 039_price_source_lukuhetki.sql
--
-- Register lukuhetki.fi as a price source (single independent shop, own
-- simpleSearch.php search and its own product page markup).

INSERT INTO suomisf.price_source (name)
VALUES ('Lukuhetki')
ON CONFLICT (name) DO NOTHING;
