-- Migration 002: EditionContributor Refactoring
-- Creates EditionContributor table and populates it from
-- existing Contributor/Part data for edition-specific roles.
--
-- Edition contributor roles: 2=Kääntäjä (translator),
-- 3=Toimittaja (editor), 4=Kansikuva (cover artist),
-- 5=Kuvittaja (illustrator), 7=Päätoimittaja (chief editor).
--
-- Safe to re-run: uses IF NOT EXISTS and ON CONFLICT DO NOTHING.

CREATE TABLE IF NOT EXISTS suomisf.editioncontributor (
    edition_id     INTEGER NOT NULL
                   REFERENCES suomisf.edition(id),
    person_id      INTEGER NOT NULL
                   REFERENCES suomisf.person(id),
    role_id        INTEGER NOT NULL
                   REFERENCES suomisf.contributorrole(id),
    real_person_id INTEGER
                   REFERENCES suomisf.person(id),
    description    VARCHAR(50),
    PRIMARY KEY (edition_id, person_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_editioncontributor_edition
    ON suomisf.editioncontributor(edition_id);

CREATE INDEX IF NOT EXISTS idx_editioncontributor_person
    ON suomisf.editioncontributor(person_id);

INSERT INTO suomisf.editioncontributor
    (edition_id, person_id, role_id, real_person_id, description)
SELECT DISTINCT
    p.edition_id,
    c.person_id,
    c.role_id,
    c.real_person_id,
    c.description
FROM suomisf.contributor c
JOIN suomisf.part p ON p.id = c.part_id
WHERE p.shortstory_id IS NULL
  AND p.edition_id   IS NOT NULL
  AND c.role_id IN (2, 3, 4, 5, 7)
ON CONFLICT (edition_id, person_id, role_id) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.editioncontributor TO mep;
