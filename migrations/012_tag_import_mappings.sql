-- Migration 012: Tag import mapping tables
--
-- Stores persistent mappings for the work tag import workflow so that
-- users do not have to re-specify replace/omit decisions each time they
-- import tags from an external source (e.g. kirjasampo.fi).
--
-- tag_import_replace: maps an external tag name to an existing local tag.
-- tag_import_omit:    marks an external tag name to be skipped on import.

CREATE TABLE IF NOT EXISTS suomisf.tag_import_replace (
    name    VARCHAR(200) NOT NULL,
    tag_id  INTEGER      NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    PRIMARY KEY (name)
);

CREATE TABLE IF NOT EXISTS suomisf.tag_import_omit (
    name    VARCHAR(200) NOT NULL,
    PRIMARY KEY (name)
);
