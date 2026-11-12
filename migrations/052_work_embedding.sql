-- Migration 052: Description vectors for similar works
--
-- scripts/work_similarity.py embeds each eligible work's description with
-- a multilingual model and keeps the vector here, so a run only embeds new
-- and changed descriptions (the first run takes about 12 minutes on a
-- workstation CPU). Rows go away with their works.
--
-- In each database where the tag_similarity role exists:
--
--   GRANT SELECT, INSERT, UPDATE, DELETE ON suomisf.work_embedding
--       TO tag_similarity;

-- One vector per work and model: float32 values, little-endian.
CREATE TABLE IF NOT EXISTS suomisf.work_embedding (
    work_id    integer NOT NULL
               REFERENCES suomisf.work(id) ON DELETE CASCADE,
    model      text NOT NULL,
    -- Hash of the embedded text; a changed description gets a new vector.
    text_hash  text NOT NULL,
    vector     bytea NOT NULL,
    updated    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (work_id, model)
);
