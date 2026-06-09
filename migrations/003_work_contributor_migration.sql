-- Migration 003: WorkContributor Refactoring
-- Creates WorkContributor table and populates it from
-- existing Contributor/Part data for work-specific roles.
--
-- Work contributor roles: 1=Kirjoittaja (author),
-- 3=Toimittaja (editor), 6=Esiintyy (appears in/subject).
--
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING.

CREATE TABLE IF NOT EXISTS suomisf.workcontributor (
    work_id        INTEGER NOT NULL
                   REFERENCES suomisf.work(id),
    person_id      INTEGER NOT NULL
                   REFERENCES suomisf.person(id),
    role_id        INTEGER NOT NULL
                   REFERENCES suomisf.contributorrole(id),
    real_person_id INTEGER
                   REFERENCES suomisf.person(id),
    description    VARCHAR(50),
    PRIMARY KEY (work_id, person_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_workcontributor_work
    ON suomisf.workcontributor(work_id);

CREATE INDEX IF NOT EXISTS idx_workcontributor_person
    ON suomisf.workcontributor(person_id);

INSERT INTO suomisf.workcontributor
    (work_id, person_id, role_id, real_person_id, description)
SELECT DISTINCT
    p.work_id,
    c.person_id,
    c.role_id,
    c.real_person_id,
    c.description
FROM suomisf.contributor c
JOIN suomisf.part p ON p.id = c.part_id
WHERE p.work_id      IS NOT NULL
  AND p.shortstory_id IS NULL
  AND c.role_id IN (1, 3, 6)
ON CONFLICT (work_id, person_id, role_id) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.workcontributor TO mep;
