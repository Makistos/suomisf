-- Migration 041: Track who added each antikvaari_price row
--
-- Needed so the prices dialog can restrict editing/deleting a price to the
-- user who added it (plus admins). Existing rows predate this and are left
-- NULL — nobody could edit/delete them except admins, which matches prior
-- behaviour for those rows. ON DELETE SET NULL rather than CASCADE since
-- antikvaari_price is append-only price history (see its class docstring)
-- and shouldn't disappear just because the adding account is later deleted.

ALTER TABLE suomisf.antikvaari_price
    ADD COLUMN user_id INTEGER REFERENCES suomisf."user"(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_antikvaari_price_user_id
    ON suomisf.antikvaari_price (user_id);
