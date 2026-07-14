-- Migration 031: add Shirley Jackson, Prometheus and Ditmar awards
--
-- Three foreign SF/fantasy awards whose winners are imported from
-- sfadb.com (their names must match impl_award_import.SFADB_AWARD_SLUGS).
-- Idempotent: inserts each only if no award with that name exists, so it
-- is safe to run on a server where they were already created.

INSERT INTO suomisf.award (name, description, domestic)
SELECT v.name, v.description, false
FROM (VALUES
    ('Shirley Jackson Award',
     'Yhdysvaltalainen kauhun, psykologisen jännityksen ja synkän '
     'fantasian kirjallisuuspalkinto.'),
    ('Prometheus Award',
     'Libertaristisen science fictionin kirjallisuuspalkinto '
     '(Libertarian Futurist Society).'),
    ('Ditmar Award',
     'Australialainen tieteis- ja fantasiakirjallisuuden fanipalkinto.')
) AS v(name, description)
WHERE NOT EXISTS (
    SELECT 1 FROM suomisf.award a WHERE a.name = v.name
);
