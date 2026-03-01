-- Migration 003: WorkContributor Refactoring
-- Creates WorkContributor table and populates it from
-- existing Contributor/Part data for work-specific roles.
--
-- Work contributor roles: 1=Kirjoittaja (author),
-- 3=Toimittaja (editor), 6=Esiintyy (appears in/subject).
--
-- Eliminates the Part indirection for work-level contributors,
-- mirroring Migration 001 (StoryContributor) and
-- Migration 002 (EditionContributor).
--
-- Run against the suomisf schema (test database).
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING.

SET search_path TO suomisf;

-- ---------------------------------------------------------------
-- 1. WorkContributor dedicated table
-- ---------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workcontributor (
    work_id        INTEGER NOT NULL
                   REFERENCES work(id),
    person_id      INTEGER NOT NULL
                   REFERENCES person(id),
    role_id        INTEGER NOT NULL
                   REFERENCES contributorrole(id),
    real_person_id INTEGER
                   REFERENCES person(id),
    description    VARCHAR(50),
    PRIMARY KEY (work_id, person_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_workcontributor_work
    ON workcontributor(work_id);

CREATE INDEX IF NOT EXISTS idx_workcontributor_person
    ON workcontributor(person_id);

-- ---------------------------------------------------------------
-- 2. Populate from existing Contributor rows via Part
--
-- Select Contributor rows that belong to Part rows with a
-- non-null work_id, null shortstory_id, and a work-specific
-- role (1, 3, 6).
-- ---------------------------------------------------------------

INSERT INTO workcontributor
    (work_id, person_id, role_id, real_person_id, description)
SELECT DISTINCT
    p.work_id,
    c.person_id,
    c.role_id,
    c.real_person_id,
    c.description
FROM contributor c
JOIN part p ON p.id = c.part_id
WHERE p.work_id      IS NOT NULL
  AND p.shortstory_id IS NULL
  AND c.role_id IN (1, 3, 6)
ON CONFLICT (work_id, person_id, role_id) DO NOTHING;

-- ---------------------------------------------------------------
-- 3. Grant privileges to application user
-- ---------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE
    ON suomisf.workcontributor TO mep;

-- ---------------------------------------------------------------
-- Phase 4 cleanup (run after all tests pass):
-- Delete work-specific roles from contributor table where
-- they have been migrated to workcontributor.
-- Uncomment when ready.
-- ---------------------------------------------------------------
-- DELETE FROM contributor
-- WHERE part_id IN (
--     SELECT p.id FROM part p
--     WHERE p.work_id IS NOT NULL
--       AND p.shortstory_id IS NULL
-- )
-- AND role_id IN (1, 3, 6);
