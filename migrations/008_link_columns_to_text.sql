-- Migration 008: Convert all link columns from VARCHAR to TEXT
--
-- VARCHAR -> TEXT in PostgreSQL is a metadata-only change (no table
-- rewrite, no index rebuild). Safe to run on a live database.
--
-- Tables affected:
--   articlelink   (VARCHAR(250) -> TEXT, NOT NULL)
--   bookserieslink (VARCHAR(200) -> TEXT, NOT NULL)
--   editionlink   (VARCHAR(200) -> TEXT, NOT NULL)
--   issue         (VARCHAR(200) -> TEXT, nullable)
--   magazine      (VARCHAR(200) -> TEXT, nullable)
--   personlink    (VARCHAR(200) -> TEXT, NOT NULL)
--   publisherlink (VARCHAR(200) -> TEXT, NOT NULL)
--   pubserieslink (VARCHAR(200) -> TEXT, NOT NULL)
--   worklink      (VARCHAR(200) -> TEXT, NOT NULL)

SET search_path TO suomisf;

ALTER TABLE articlelink   ALTER COLUMN link TYPE TEXT;
ALTER TABLE bookserieslink ALTER COLUMN link TYPE TEXT;
ALTER TABLE editionlink   ALTER COLUMN link TYPE TEXT;
ALTER TABLE issue         ALTER COLUMN link TYPE TEXT;
ALTER TABLE magazine      ALTER COLUMN link TYPE TEXT;
ALTER TABLE personlink    ALTER COLUMN link TYPE TEXT;
ALTER TABLE publisherlink ALTER COLUMN link TYPE TEXT;
ALTER TABLE pubserieslink ALTER COLUMN link TYPE TEXT;
ALTER TABLE worklink      ALTER COLUMN link TYPE TEXT;
