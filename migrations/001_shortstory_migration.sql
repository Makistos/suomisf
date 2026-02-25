-- Migration 001: ShortStory Refactoring
-- Creates EditionShortStory junction table and StoryContributor table.
-- Populates them from existing Part/Contributor data.
--
-- Run against the suomisf schema (test database).
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING.

SET search_path TO suomisf;

-- ---------------------------------------------------------------
-- 1. EditionShortStory junction table
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS editionshortstory (
    edition_id    INTEGER NOT NULL
                  REFERENCES edition(id),
    shortstory_id INTEGER NOT NULL
                  REFERENCES shortstory(id),
    order_num     INTEGER,
    PRIMARY KEY (edition_id, shortstory_id)
);

CREATE INDEX IF NOT EXISTS idx_editionshortstory_edition
    ON editionshortstory(edition_id);

CREATE INDEX IF NOT EXISTS idx_editionshortstory_short
    ON editionshortstory(shortstory_id);

-- Populate from existing Part rows where both edition_id
-- and shortstory_id are set.
INSERT INTO editionshortstory (edition_id, shortstory_id, order_num)
SELECT DISTINCT
    p.edition_id,
    p.shortstory_id,
    p.order_num
FROM part p
WHERE p.shortstory_id IS NOT NULL
  AND p.edition_id   IS NOT NULL
ON CONFLICT (edition_id, shortstory_id) DO NOTHING;

-- ---------------------------------------------------------------
-- 2. StoryContributor dedicated table
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS storycontributor (
    shortstory_id  INTEGER NOT NULL
                   REFERENCES shortstory(id),
    person_id      INTEGER NOT NULL
                   REFERENCES person(id),
    role_id        INTEGER NOT NULL
                   REFERENCES contributorrole(id),
    real_person_id INTEGER
                   REFERENCES person(id),
    description    VARCHAR(50),
    PRIMARY KEY (shortstory_id, person_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_storycontributor_short
    ON storycontributor(shortstory_id);

CREATE INDEX IF NOT EXISTS idx_storycontributor_person
    ON storycontributor(person_id);

-- Populate from existing Contributor rows that belong to
-- Part rows that have a shortstory_id.
INSERT INTO storycontributor
    (shortstory_id, person_id, role_id, real_person_id, description)
SELECT DISTINCT
    p.shortstory_id,
    c.person_id,
    c.role_id,
    c.real_person_id,
    c.description
FROM contributor c
JOIN part p ON p.id = c.part_id
WHERE p.shortstory_id IS NOT NULL
ON CONFLICT (shortstory_id, person_id, role_id) DO NOTHING;
