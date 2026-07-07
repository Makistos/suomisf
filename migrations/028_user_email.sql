-- Add email address to users (for password reset). Nullable so existing
-- users are unaffected; unique index allows multiple NULLs in Postgres.
ALTER TABLE suomisf."user"
    ADD COLUMN IF NOT EXISTS email character varying(120);

CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email
    ON suomisf."user" (email);
