-- Migration 051: Similar works recommendations
--
-- Written by scripts/work_similarity.py (see docs/work-similarity-plan.md),
-- read by GET /api/works/<id>/similar. Rows go away with their works.
--
-- The script connects as the tag_similarity role (migration 044); in each
-- database where that role exists, also:
--
--   GRANT SELECT ON suomisf.work, suomisf.workgenre,
--       suomisf.workcontributor, suomisf.bookseries, suomisf.omnibus
--       TO tag_similarity;
--   GRANT SELECT, INSERT, UPDATE, DELETE
--       ON suomisf.work_similarity, suomisf.work_similarity_run
--       TO tag_similarity;

-- The ranked list of each work, best first.
CREATE TABLE IF NOT EXISTS suomisf.work_similarity (
    source_work_id    integer NOT NULL
                      REFERENCES suomisf.work(id) ON DELETE CASCADE,
    target_work_id    integer NOT NULL
                      REFERENCES suomisf.work(id) ON DELETE CASCADE,
    rank              smallint NOT NULL,
    score             real NOT NULL,
    -- Per signal (T, D, G, Y), per tag type and the coverage.
    signal_scores     jsonb NOT NULL,
    -- [{"type": <tagtype id>, "tags": [tag ids]}], biggest contribution
    -- first.
    reasons           jsonb NOT NULL,
    algorithm_version integer NOT NULL,
    computed_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_work_id, target_work_id),
    CHECK (source_work_id <> target_work_id)
);

CREATE INDEX IF NOT EXISTS ix_work_similarity_source_rank
    ON suomisf.work_similarity (source_work_id, rank);
CREATE INDEX IF NOT EXISTS ix_work_similarity_target
    ON suomisf.work_similarity (target_work_id);

-- What the last full run was computed from: a run whose inputs hash to
-- the same value has nothing to do.
CREATE TABLE IF NOT EXISTS suomisf.work_similarity_run (
    id                integer PRIMARY KEY CHECK (id = 1),
    algorithm_version integer NOT NULL,
    input_hash        text NOT NULL,
    eligible_works    integer NOT NULL,
    computed_at       timestamptz NOT NULL DEFAULT now()
);
