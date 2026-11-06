-- Migration 049: suggested pairs checked by an admin
--
-- An admin marks a suggestion as checked (correct as it is), so the admin
-- card can tell reviewed pairs from the rest. scripts/tag_similarity.py
-- keeps a checked pair even if its rules no longer find it.

ALTER TABLE suomisf.tag_similarity
    ADD COLUMN IF NOT EXISTS checked boolean NOT NULL DEFAULT false;
