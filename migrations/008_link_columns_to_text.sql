-- Migration 008: Convert link and description columns to TEXT
--
-- VARCHAR -> TEXT in PostgreSQL is a metadata-only change (no table
-- rewrite, no index rebuild). Safe to run on a live database.
--
-- link columns affected:
--   articlelink    (VARCHAR(250) -> TEXT, NOT NULL)
--   bookserieslink (VARCHAR(200) -> TEXT, NOT NULL)
--   editionlink    (VARCHAR(200) -> TEXT, NOT NULL)
--   issue          (VARCHAR(200) -> TEXT, nullable)
--   magazine       (VARCHAR(200) -> TEXT, nullable)
--   personlink     (VARCHAR(200) -> TEXT, NOT NULL)
--   publisherlink  (VARCHAR(200) -> TEXT, NOT NULL)
--   pubserieslink  (VARCHAR(200) -> TEXT, NOT NULL)
--   worklink       (VARCHAR(200) -> TEXT, NOT NULL)
--
-- description columns affected:
--   articlelink    (VARCHAR(100) -> TEXT, nullable)
--   bookserieslink (VARCHAR(100) -> TEXT, nullable)
--   editionlink    (VARCHAR(100) -> TEXT, nullable)
--   personlink     (VARCHAR(100) -> TEXT, nullable)
--   publisherlink  (VARCHAR(100) -> TEXT, nullable)
--   pubserieslink  (VARCHAR(100) -> TEXT, nullable)
--   worklink       (VARCHAR(100) -> TEXT, nullable)

SET search_path TO suomisf;

ALTER TABLE articlelink    ALTER COLUMN link        TYPE TEXT;
ALTER TABLE bookserieslink ALTER COLUMN link        TYPE TEXT;
ALTER TABLE editionlink    ALTER COLUMN link        TYPE TEXT;
ALTER TABLE issue          ALTER COLUMN link        TYPE TEXT;
ALTER TABLE magazine       ALTER COLUMN link        TYPE TEXT;
ALTER TABLE personlink     ALTER COLUMN link        TYPE TEXT;
ALTER TABLE publisherlink  ALTER COLUMN link        TYPE TEXT;
ALTER TABLE pubserieslink  ALTER COLUMN link        TYPE TEXT;
ALTER TABLE worklink       ALTER COLUMN link        TYPE TEXT;

ALTER TABLE articlelink    ALTER COLUMN description TYPE TEXT;
ALTER TABLE bookserieslink ALTER COLUMN description TYPE TEXT;
ALTER TABLE editionlink    ALTER COLUMN description TYPE TEXT;
ALTER TABLE personlink     ALTER COLUMN description TYPE TEXT;
ALTER TABLE publisherlink  ALTER COLUMN description TYPE TEXT;
ALTER TABLE pubserieslink  ALTER COLUMN description TYPE TEXT;
ALTER TABLE worklink       ALTER COLUMN description TYPE TEXT;
