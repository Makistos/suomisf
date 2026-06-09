-- Migration 008: Convert link and description columns to TEXT
--
-- VARCHAR -> TEXT in PostgreSQL is a metadata-only change (no table
-- rewrite, no index rebuild). Safe to run on a live database.

ALTER TABLE suomisf.articlelink    ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.bookserieslink ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.editionlink    ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.issue          ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.magazine       ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.personlink     ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.publisherlink  ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.pubserieslink  ALTER COLUMN link        TYPE TEXT;
ALTER TABLE suomisf.worklink       ALTER COLUMN link        TYPE TEXT;

ALTER TABLE suomisf.articlelink    ALTER COLUMN description TYPE TEXT;
ALTER TABLE suomisf.bookserieslink ALTER COLUMN description TYPE TEXT;
ALTER TABLE suomisf.editionlink    ALTER COLUMN description TYPE TEXT;
ALTER TABLE suomisf.personlink     ALTER COLUMN description TYPE TEXT;
ALTER TABLE suomisf.publisherlink  ALTER COLUMN description TYPE TEXT;
ALTER TABLE suomisf.pubserieslink  ALTER COLUMN description TYPE TEXT;
ALTER TABLE suomisf.worklink       ALTER COLUMN description TYPE TEXT;
