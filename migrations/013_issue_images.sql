-- Migration 013: Issue image table
--
-- Adds a dedicated issueimage table to support multiple images per issue,
-- matching the structure of editionimage. Existing image_src and image_attr
-- values from the issue table are migrated into the new table.

SET search_path TO suomisf;

CREATE TABLE IF NOT EXISTS issueimage (
    id         BIGSERIAL    PRIMARY KEY,
    issue_id   BIGINT       NOT NULL REFERENCES issue(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    image_src  VARCHAR(200) NOT NULL,
    image_attr VARCHAR(100) DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS issueimage_issue_id ON issueimage(issue_id);

INSERT INTO issueimage (issue_id, image_src, image_attr)
    SELECT id, image_src, image_attr
    FROM issue
    WHERE image_src IS NOT NULL;
