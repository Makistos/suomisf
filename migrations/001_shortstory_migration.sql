-- Migration 001: ShortStory Refactoring
-- Creates EditionShortStory junction table and StoryContributor table.
-- Populates them from existing Part/Contributor data.
--
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING.

CREATE TABLE IF NOT EXISTS suomisf.editionshortstory (
    edition_id    INTEGER NOT NULL
                  REFERENCES suomisf.edition(id),
    shortstory_id INTEGER NOT NULL
                  REFERENCES suomisf.shortstory(id),
    order_num     INTEGER,
    PRIMARY KEY (edition_id, shortstory_id)
);

CREATE INDEX IF NOT EXISTS idx_editionshortstory_edition
    ON suomisf.editionshortstory(edition_id);

CREATE INDEX IF NOT EXISTS idx_editionshortstory_short
    ON suomisf.editionshortstory(shortstory_id);

INSERT INTO suomisf.editionshortstory (edition_id, shortstory_id, order_num)
SELECT DISTINCT
    p.edition_id,
    p.shortstory_id,
    p.order_num
FROM suomisf.part p
WHERE p.shortstory_id IS NOT NULL
  AND p.edition_id   IS NOT NULL
ON CONFLICT (edition_id, shortstory_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS suomisf.storycontributor (
    shortstory_id  INTEGER NOT NULL
                   REFERENCES suomisf.shortstory(id),
    person_id      INTEGER NOT NULL
                   REFERENCES suomisf.person(id),
    role_id        INTEGER NOT NULL
                   REFERENCES suomisf.contributorrole(id),
    real_person_id INTEGER
                   REFERENCES suomisf.person(id),
    description    VARCHAR(50),
    PRIMARY KEY (shortstory_id, person_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_storycontributor_short
    ON suomisf.storycontributor(shortstory_id);

CREATE INDEX IF NOT EXISTS idx_storycontributor_person
    ON suomisf.storycontributor(person_id);

CREATE OR REPLACE VIEW suomisf.work_shortstory AS
SELECT
    p.work_id,
    ess.shortstory_id,
    MIN(ess.order_num) AS order_num
FROM suomisf.editionshortstory ess
JOIN suomisf.part p ON p.edition_id = ess.edition_id
WHERE p.work_id IS NOT NULL
  AND p.shortstory_id IS NULL
GROUP BY p.work_id, ess.shortstory_id;

INSERT INTO suomisf.storycontributor
    (shortstory_id, person_id, role_id, real_person_id, description)
SELECT DISTINCT
    p.shortstory_id,
    c.person_id,
    c.role_id,
    c.real_person_id,
    c.description
FROM suomisf.contributor c
JOIN suomisf.part p ON p.id = c.part_id
WHERE p.shortstory_id IS NOT NULL
ON CONFLICT (shortstory_id, person_id, role_id) DO NOTHING;

GRANT SELECT ON suomisf.work_shortstory TO mep;
GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.editionshortstory TO mep;
GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.storycontributor TO mep;
