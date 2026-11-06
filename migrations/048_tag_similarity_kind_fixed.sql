-- Migration 048: pair kinds set by an admin
--
-- An admin can mark a suggested duplicate as only related, or the other
-- way round. scripts/tag_similarity.py then keeps that kind, and keeps
-- the pair even if its rules no longer find it.

ALTER TABLE suomisf.tag_similarity
    ADD COLUMN IF NOT EXISTS kind_fixed boolean NOT NULL DEFAULT false;
