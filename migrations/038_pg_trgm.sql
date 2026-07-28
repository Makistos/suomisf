-- 038_pg_trgm.sql
--
-- Enable the pg_trgm trigram extension, used by the titles-only search mode to
-- require that a matched title/name actually resembles the search term. This
-- filters out voikko compound-splitting noise (e.g. "maailma" -> "maa"+"ilma"
-- making every "maailma" title match a search for "yläilmoissa").
--
-- NOTE: CREATE EXTENSION requires a superuser or a role with CREATE privilege
-- on the database; run as such on the deployment server.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
