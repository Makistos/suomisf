-- Migration 042: Comment on a read work
--
-- A free-text note the user writes when marking a work read, like the
-- description on an owned edition (userbook.description). NULL = no note.
--
-- Some databases have userwork in the public schema (migration 033 was run
-- with public first on the search path) and an empty copy in suomisf; the
-- app uses whichever comes first on the search path. Add the column to
-- every copy that exists.

DO $$
BEGIN
    IF to_regclass('public.userwork') IS NOT NULL THEN
        ALTER TABLE public.userwork
            ADD COLUMN IF NOT EXISTS description VARCHAR(500);
    END IF;
    IF to_regclass('suomisf.userwork') IS NOT NULL THEN
        ALTER TABLE suomisf.userwork
            ADD COLUMN IF NOT EXISTS description VARCHAR(500);
    END IF;
END $$;
