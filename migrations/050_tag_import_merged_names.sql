-- Migration 050: Kirjasampo names for tags merged before this
--
-- Merging a tag now saves its name (without parenthesised qualifiers, in
-- lower case) as a Kirjasampo name for the kept tag, so the import offers
-- the kept tag instead of a new one. This saves the names of the merges
-- the change log records, latest merge first, with the same rules: a name
-- already mapped or omitted keeps that decision, a name a tag still has is
-- left for it, and a merge whose kept tag is gone is skipped.
-- Safe to run again.

INSERT INTO suomisf.tag_import_replace (name, tag_id)
SELECT DISTINCT ON (m.name) m.name, m.tag_id
  FROM (SELECT lower(btrim(regexp_replace(
                   regexp_replace(old_value, '\s*\([^)]*\)', ' ', 'g'),
                   ' {2,}', ' ', 'g'), ' ')) AS name,
               table_id AS tag_id, date
          FROM suomisf.log
         WHERE table_name = 'Asiasana' AND field_name = 'Yhdistetty') m
 WHERE m.name <> ''
   AND EXISTS (SELECT 1 FROM suomisf.tag t WHERE t.id = m.tag_id)
   AND NOT EXISTS (SELECT 1 FROM suomisf.tag t WHERE lower(t.name) = m.name)
   AND NOT EXISTS (SELECT 1 FROM suomisf.tag_import_omit o
                    WHERE o.name = m.name)
 ORDER BY m.name, m.date DESC
    ON CONFLICT (name) DO NOTHING;
