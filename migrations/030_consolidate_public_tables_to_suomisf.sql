-- Migration 030: consolidate application tables into the suomisf schema
--
-- Several tables added by earlier migrations ended up in the *public*
-- schema on some servers:
--   awardlink, issueimage, antikvaari_excluded_book,
--   tag_import_omit, tag_import_replace, award_import_source
--
-- Cause: their ORM models lacked an explicit {'schema': 'suomisf'}, and
-- app import runs Base.metadata.create_all(), which created the missing
-- tables in the default (public) schema. The application then read and
-- wrote those public copies, so the public copies are authoritative; the
-- suomisf copies created by the original migrations are stale.
--
-- This moves each live public table into suomisf (preserving its data and
-- id sequence) and drops the stale suomisf copy, so every application
-- table lives in suomisf and is captured by `pg_dump -n suomisf`.
--
-- SAFETY: take a full backup first. Verify the public copy is the
-- authoritative one before running, e.g.:
--   SELECT (SELECT count(*) FROM public.awardlink),
--          (SELECT count(*) FROM suomisf.awardlink);
-- The public count should be >= the suomisf count for each table (the app
-- writes to public). This migration keeps the public data and discards the
-- stale suomisf copy.

DO $$
DECLARE
    t text;
    tables text[] := ARRAY[
        'awardlink', 'issueimage', 'antikvaari_excluded_book',
        'tag_import_omit', 'tag_import_replace', 'award_import_source'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        IF EXISTS (SELECT 1 FROM pg_tables
                   WHERE schemaname = 'public' AND tablename = t) THEN
            -- Drop the stale suomisf copy, then move the live public table.
            EXECUTE format('DROP TABLE IF EXISTS suomisf.%I CASCADE', t);
            EXECUTE format('ALTER TABLE public.%I SET SCHEMA suomisf', t);
            -- Move the owned id sequence too, if the table has one.
            IF EXISTS (SELECT 1 FROM pg_sequences
                       WHERE schemaname = 'public'
                         AND sequencename = t || '_id_seq') THEN
                EXECUTE format(
                    'ALTER SEQUENCE public.%I SET SCHEMA suomisf',
                    t || '_id_seq');
            END IF;
        END IF;
    END LOOP;
END $$;
