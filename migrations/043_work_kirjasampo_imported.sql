-- Migration 043: When Kirjasampo tags were last imported into a work
--
-- Set by POST /api/work/<id>/tags/import (the "Tuo Kirjasampo-asiasanat"
-- dialog) each time an admin saves it. NULL = never imported.

ALTER TABLE suomisf.work
    ADD COLUMN IF NOT EXISTS kirjasampo_imported TIMESTAMP WITH TIME ZONE;
