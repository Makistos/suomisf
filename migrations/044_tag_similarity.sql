-- Migration 044: Tag similarity suggestions
--
-- Written by scripts/tag_similarity.py (see docs/tag-similarity-plan.md),
-- read and decided on by admins. Rows go away with their tags, so a tag
-- merge or delete needs nothing else.
--
-- The script connects as its own role; create it once per database
-- (roles are per cluster, so not here):
--
--   CREATE ROLE tag_similarity LOGIN PASSWORD '...';
--   GRANT USAGE ON SCHEMA suomisf TO tag_similarity;
--   GRANT SELECT ON suomisf.tag, suomisf.worktag, suomisf.storytag,
--       suomisf.articletag TO tag_similarity;
--   GRANT SELECT, INSERT, UPDATE, DELETE
--       ON suomisf.tag_embedding, suomisf.tag_similarity TO tag_similarity;

-- One vector per tag and model: float32 values, little-endian.
CREATE TABLE IF NOT EXISTS suomisf.tag_embedding (
    tag_id     integer NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    model      text NOT NULL,
    -- Hash of the embedded text; a renamed tag gets a new vector.
    text_hash  text NOT NULL,
    vector     bytea NOT NULL,
    updated    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tag_id, model)
);

CREATE TABLE IF NOT EXISTS suomisf.tag_similarity (
    tag_a        integer NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    tag_b        integer NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    kind         text NOT NULL
                 CHECK (kind IN ('duplicate', 'related')),
    -- Rule that found the pair.
    reason       text NOT NULL
                 CHECK (reason IN ('baseform', 'spelling', 'name', 'usage')),
    name_score   real,
    containment  real,
    shared       integer NOT NULL DEFAULT 0,
    -- 'dismissed' = an admin said the tags are different; the job never
    -- changes it.
    status       text NOT NULL DEFAULT 'new'
                 CHECK (status IN ('new', 'dismissed')),
    decided_by   integer REFERENCES suomisf."user"(id) ON DELETE SET NULL,
    decided_at   timestamptz,
    updated      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tag_a, tag_b),
    CHECK (tag_a < tag_b)
);

CREATE INDEX IF NOT EXISTS tag_similarity_tag_b_idx
    ON suomisf.tag_similarity (tag_b);
