-- Migration 002: EditionContributor Refactoring
-- Creates EditionContributor table and populates it from
-- existing Contributor/Part data for edition-specific roles.
--
-- Edition contributor roles: 2=Kääntäjä (translator),
-- 3=Toimittaja (editor), 4=Kansikuva (cover artist),
-- 5=Kuvittaja (illustrator), 7=Päätoimittaja (chief editor).
--
-- Authors (role 1) and subject appearances (role 6) remain
-- in the contributor table via Part (work-level relationships).
--
-- Run against the suomisf schema (test database).
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING.

SET search_path TO suomisf;

-- ---------------------------------------------------------------
-- 1. EditionContributor dedicated table
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS editioncontributor (
    edition_id     INTEGER NOT NULL
                   REFERENCES edition(id),
    person_id      INTEGER NOT NULL
                   REFERENCES person(id),
    role_id        INTEGER NOT NULL
                   REFERENCES contributorrole(id),
    real_person_id INTEGER
                   REFERENCES person(id),
    description    VARCHAR(50),
    PRIMARY KEY (edition_id, person_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_editioncontributor_edition
    ON editioncontributor(edition_id);

CREATE INDEX IF NOT EXISTS idx_editioncontributor_person
    ON editioncontributor(person_id);

-- ---------------------------------------------------------------
-- 2. Populate from existing Contributor rows via Part
--
-- Select Contributor rows that belong to Part rows with a
-- non-null edition_id, null shortstory_id, and an edition-
-- specific role (2, 3, 4, 5, 7).
-- ---------------------------------------------------------------

INSERT INTO editioncontributor
    (edition_id, person_id, role_id, real_person_id, description)
SELECT DISTINCT
    p.edition_id,
    c.person_id,
    c.role_id,
    c.real_person_id,
    c.description
FROM contributor c
JOIN part p ON p.id = c.part_id
WHERE p.shortstory_id IS NULL
  AND p.edition_id   IS NOT NULL
  AND c.role_id IN (2, 3, 4, 5, 7)
ON CONFLICT (edition_id, person_id, role_id) DO NOTHING;

-- ---------------------------------------------------------------
-- 3. Grant privileges to application user
-- ---------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE
    ON suomisf.editioncontributor TO mep;

-- ---------------------------------------------------------------
-- Phase 4 cleanup (run after all tests pass):
-- Delete edition-specific roles from contributor table where
-- they have been migrated to editioncontributor.
-- Uncomment when ready.
-- ---------------------------------------------------------------
-- DELETE FROM contributor
-- WHERE part_id IN (
--     SELECT p.id FROM part p
--     WHERE p.shortstory_id IS NULL
--       AND p.edition_id IS NOT NULL
-- )
-- AND role_id IN (2, 3, 4, 5, 7);
