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
--
-- Tables with fts: award, bookseries, person, publisher, pubseries,
--                  shortstory, tag, work
-- Tables without fts: country, language

SET search_path TO suomisf, public;

-- ----------------------------------------------------------------
-- country, language: no fts dependency, simple alter
-- ----------------------------------------------------------------

ALTER TABLE country
    ALTER COLUMN name TYPE VARCHAR(50) COLLATE "fi-x-icu";

ALTER TABLE language
    ALTER COLUMN name TYPE VARCHAR(50) COLLATE "fi-x-icu";

-- ----------------------------------------------------------------
-- award
-- ----------------------------------------------------------------

ALTER TABLE award DROP COLUMN fts;
ALTER TABLE award
    ALTER COLUMN name TYPE VARCHAR(100) COLLATE "fi-x-icu";
ALTER TABLE award
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'B')
    ) STORED;

-- ----------------------------------------------------------------
-- bookseries
-- ----------------------------------------------------------------

ALTER TABLE bookseries DROP COLUMN fts;
ALTER TABLE bookseries
    ALTER COLUMN name TYPE VARCHAR(250) COLLATE "fi-x-icu";
ALTER TABLE bookseries
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(orig_name, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'C')
    ) STORED;

-- ----------------------------------------------------------------
-- person
-- ----------------------------------------------------------------

ALTER TABLE person DROP COLUMN fts;
ALTER TABLE person
    ALTER COLUMN name     TYPE VARCHAR(250) COLLATE "fi-x-icu",
    ALTER COLUMN alt_name TYPE VARCHAR(250) COLLATE "fi-x-icu";
ALTER TABLE person
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

-- ----------------------------------------------------------------
-- publisher
-- ----------------------------------------------------------------

ALTER TABLE publisher DROP COLUMN fts;
ALTER TABLE publisher
    ALTER COLUMN name TYPE VARCHAR(500) COLLATE "fi-x-icu";
ALTER TABLE publisher
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(fullname, '')::text), 'B') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'C')
    ) STORED;

-- ----------------------------------------------------------------
-- pubseries
-- ----------------------------------------------------------------

ALTER TABLE pubseries DROP COLUMN fts;
ALTER TABLE pubseries
    ALTER COLUMN name TYPE VARCHAR(250) COLLATE "fi-x-icu";
ALTER TABLE pubseries
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'B')
    ) STORED;

-- ----------------------------------------------------------------
-- shortstory
-- ----------------------------------------------------------------

ALTER TABLE shortstory DROP COLUMN fts;
ALTER TABLE shortstory
    ALTER COLUMN title      TYPE VARCHAR(700) COLLATE "fi-x-icu",
    ALTER COLUMN orig_title TYPE VARCHAR(700) COLLATE "fi-x-icu";
ALTER TABLE shortstory
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(title, '')::text), 'A')
    ) STORED;

-- ----------------------------------------------------------------
-- tag
-- ----------------------------------------------------------------

ALTER TABLE tag DROP COLUMN fts;
ALTER TABLE tag
    ALTER COLUMN name TYPE VARCHAR(100) COLLATE "fi-x-icu";
ALTER TABLE tag
    ADD COLUMN fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('voikko',
            COALESCE(name, '')::text), 'A') ||
        setweight(to_tsvector('voikko',
            COALESCE(description, '')), 'B')
    ) STORED;

-- ----------------------------------------------------------------
-- work
-- ----------------------------------------------------------------

ALTER TABLE work DROP COLUMN fts;
ALTER TABLE work
    ALTER COLUMN title      TYPE VARCHAR(500) COLLATE "fi-x-icu",
    ALTER COLUMN orig_title TYPE VARCHAR(500) COLLATE "fi-x-icu",
    ALTER COLUMN author_str TYPE VARCHAR(500) COLLATE "fi-x-icu";
ALTER TABLE work
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

-- ----------------------------------------------------------------
-- Recreate GIN indexes on fts columns
-- ----------------------------------------------------------------

CREATE INDEX idx_award_fts      ON award      USING GIN (fts);
CREATE INDEX idx_bookseries_fts ON bookseries  USING GIN (fts);
CREATE INDEX idx_person_fts     ON person      USING GIN (fts);
CREATE INDEX idx_publisher_fts  ON publisher   USING GIN (fts);
CREATE INDEX idx_pubseries_fts  ON pubseries   USING GIN (fts);
CREATE INDEX idx_shortstory_fts ON shortstory  USING GIN (fts);
CREATE INDEX idx_tag_fts        ON tag         USING GIN (fts);
CREATE INDEX idx_work_fts       ON work        USING GIN (fts);
