-- Migration 009: Set Finnish collation on name/title columns
--
-- The database default (en_US.UTF-8) sorts ä/ö/å alongside a/o/a.
-- Finnish/Swedish alphabetical order places ä, å, ö after z.
-- PostgreSQL's fi-x-icu collation implements this correctly.
--
-- Several tables have a generated 'fts' tsvector column that
-- depends on the name/title columns. PostgreSQL requires that the
-- generated column be dropped and recreated when changing the type
-- of a column it depends on.

ALTER TABLE suomisf.country
    ALTER COLUMN name TYPE VARCHAR(50) COLLATE "fi-x-icu";

ALTER TABLE suomisf.language
    ALTER COLUMN name TYPE VARCHAR(50) COLLATE "fi-x-icu";

ALTER TABLE suomisf.award DROP COLUMN fts;
ALTER TABLE suomisf.award
    ALTER COLUMN name TYPE VARCHAR(100) COLLATE "fi-x-icu";
ALTER TABLE suomisf.award
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'B')
    ) STORED;

ALTER TABLE suomisf.bookseries DROP COLUMN fts;
ALTER TABLE suomisf.bookseries
    ALTER COLUMN name TYPE VARCHAR(250) COLLATE "fi-x-icu";
ALTER TABLE suomisf.bookseries
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(orig_name, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'C')
    ) STORED;

ALTER TABLE suomisf.person DROP COLUMN fts;
ALTER TABLE suomisf.person
    ALTER COLUMN name     TYPE VARCHAR(250) COLLATE "fi-x-icu",
    ALTER COLUMN alt_name TYPE VARCHAR(250) COLLATE "fi-x-icu";
ALTER TABLE suomisf.person
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(fullname, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(other_names, '')), 'C') ||
        setweight(to_tsvector('voikko',
            COALESCE(alt_name, '')::text), 'C') ||
        setweight(to_tsvector('voikko',
            COALESCE(bio, '')), 'D')
    ) STORED;

ALTER TABLE suomisf.publisher DROP COLUMN fts;
ALTER TABLE suomisf.publisher
    ALTER COLUMN name TYPE VARCHAR(500) COLLATE "fi-x-icu";
ALTER TABLE suomisf.publisher
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(fullname, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'C')
    ) STORED;

ALTER TABLE suomisf.pubseries DROP COLUMN fts;
ALTER TABLE suomisf.pubseries
    ALTER COLUMN name TYPE VARCHAR(250) COLLATE "fi-x-icu";
ALTER TABLE suomisf.pubseries
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'B')
    ) STORED;

ALTER TABLE suomisf.shortstory DROP COLUMN fts;
ALTER TABLE suomisf.shortstory
    ALTER COLUMN title      TYPE VARCHAR(700) COLLATE "fi-x-icu",
    ALTER COLUMN orig_title TYPE VARCHAR(700) COLLATE "fi-x-icu";
ALTER TABLE suomisf.shortstory
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(title, '')::text), 'A')
    ) STORED;

ALTER TABLE suomisf.tag DROP COLUMN fts;
ALTER TABLE suomisf.tag
    ALTER COLUMN name TYPE VARCHAR(100) COLLATE "fi-x-icu";
ALTER TABLE suomisf.tag
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'B')
    ) STORED;

ALTER TABLE suomisf.work DROP COLUMN fts;
ALTER TABLE suomisf.work
    ALTER COLUMN title      TYPE VARCHAR(500) COLLATE "fi-x-icu",
    ALTER COLUMN orig_title TYPE VARCHAR(500) COLLATE "fi-x-icu",
    ALTER COLUMN author_str TYPE VARCHAR(500) COLLATE "fi-x-icu";
ALTER TABLE suomisf.work
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(title, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(subtitle, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(orig_title, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(misc, '')::text), 'C') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'D')
    ) STORED;

CREATE INDEX idx_award_fts      ON suomisf.award      USING GIN (fts);
CREATE INDEX idx_bookseries_fts ON suomisf.bookseries  USING GIN (fts);
CREATE INDEX idx_person_fts     ON suomisf.person      USING GIN (fts);
CREATE INDEX idx_publisher_fts  ON suomisf.publisher   USING GIN (fts);
CREATE INDEX idx_pubseries_fts  ON suomisf.pubseries   USING GIN (fts);
CREATE INDEX idx_shortstory_fts ON suomisf.shortstory  USING GIN (fts);
CREATE INDEX idx_tag_fts        ON suomisf.tag         USING GIN (fts);
CREATE INDEX idx_work_fts       ON suomisf.work        USING GIN (fts);
