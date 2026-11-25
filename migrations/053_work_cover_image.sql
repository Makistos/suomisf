-- Migration 053: The cover an admin picked for a work's page
--
-- Set by PUT /api/works/<id>/cover. NULL = the page picks a cover itself
-- (the first printing with one). A deleted image clears the choice.

ALTER TABLE suomisf.work
    ADD COLUMN IF NOT EXISTS cover_image_id INTEGER
    REFERENCES suomisf.editionimage(id) ON DELETE SET NULL;
