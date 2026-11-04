-- Migration 045: Wikidata places of Paikka tags
--
-- Written by scripts/tag_similarity.py: the Wikidata item a Paikka tag
-- names, and the places that item is located in, so a rerun looks up only
-- new and renamed tags. Tags in the same place, or one inside the other,
-- become tag_similarity pairs with reason 'place'.
--
-- The tag_similarity role (migration 044) also needs:
--
--   GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.tag_place
--       TO tag_similarity;

CREATE TABLE IF NOT EXISTS suomisf.tag_place (
    tag_id       integer PRIMARY KEY
                 REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    -- Hash of the tag name looked up; a renamed tag is looked up again.
    name_hash    text NOT NULL,
    -- NULL = not a real place (a kind of place, fictional, no match).
    qid          text,
    label        text,
    description  text,
    -- {qid: depth} reached through "located in" (P131) and country (P17),
    -- and the same with continent (P30), used when the first has no tag.
    ancestors    jsonb NOT NULL DEFAULT '{}',
    continent_ancestors jsonb NOT NULL DEFAULT '{}',
    -- Set by hand; the job never looks the tag up again.
    manual       boolean NOT NULL DEFAULT false,
    checked      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE suomisf.tag_similarity
    DROP CONSTRAINT IF EXISTS tag_similarity_reason_check;
ALTER TABLE suomisf.tag_similarity
    ADD CONSTRAINT tag_similarity_reason_check
    CHECK (reason IN ('baseform', 'spelling', 'place', 'name', 'usage'));
