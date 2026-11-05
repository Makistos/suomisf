-- Migration 047: KOKO concepts of tags (Finto)
--
-- Written by scripts/tag_similarity.py: the KOKO concept (Finto's
-- combined Finnish ontology, which joins KAUNO, YSO and others) whose
-- label a tag has, so a rerun looks up only new and renamed tags. Tags of
-- the same concept, or of concepts KOKO links as related, become related
-- tag_similarity pairs with reason 'concept' or 'concept_related'.
--
-- The tag_similarity role (migration 044) also needs:
--
--   GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.tag_finto
--       TO tag_similarity;

CREATE TABLE IF NOT EXISTS suomisf.tag_finto (
    tag_id    integer PRIMARY KEY
              REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    -- Hash of the tag name looked up; a renamed tag is looked up again.
    name_hash text NOT NULL,
    -- NULL = no concept, or several with that label.
    uri       text,
    label     text,
    -- KAUNO/YSO concepts the KOKO concept matches, and the concepts it
    -- is related to (skos:exactMatch/closeMatch, skos:related).
    matches   jsonb NOT NULL DEFAULT '[]',
    related   jsonb NOT NULL DEFAULT '[]',
    -- Set by hand; the job never looks the tag up again.
    manual    boolean NOT NULL DEFAULT false,
    checked   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE suomisf.tag_similarity
    DROP CONSTRAINT IF EXISTS tag_similarity_reason_check;
ALTER TABLE suomisf.tag_similarity
    ADD CONSTRAINT tag_similarity_reason_check
    CHECK (reason IN ('baseform', 'spelling', 'place', 'name', 'usage',
                      'manual', 'concept', 'concept_related'));
