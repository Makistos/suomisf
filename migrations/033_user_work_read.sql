-- Migration 033: Per-user "read" status for works
--
-- Records that a user has read a work (a row means "read"), plus an optional
-- opinion. This is work-level and independent of ownership: a user can mark a
-- work read without owning any of its editions.
--
--   opinion : -1 = didn't like, 0 = it was ok, 1 = liked.
--             NULL = read but no opinion given.

CREATE TABLE IF NOT EXISTS suomisf.userwork (
    user_id  INTEGER  NOT NULL
        REFERENCES suomisf."user"(id) ON DELETE CASCADE,
    work_id  INTEGER  NOT NULL
        REFERENCES suomisf.work(id) ON DELETE CASCADE,
    opinion  SMALLINT,
    added    TIMESTAMP DEFAULT now(),
    PRIMARY KEY (user_id, work_id)
);

CREATE INDEX IF NOT EXISTS ix_userwork_user_id
    ON suomisf.userwork (user_id);
CREATE INDEX IF NOT EXISTS ix_userwork_work_id
    ON suomisf.userwork (work_id);
