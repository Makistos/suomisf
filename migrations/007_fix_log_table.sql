-- Migration 007: Fix log table — merge public."Log" into suomisf.log
--
-- SQLAlchemy's __tablename__ = 'Log' (capital L) caused create_all() to
-- create a case-sensitive public."Log" table. All log_changes() writes
-- since September 2025 went there instead of suomisf.log.
--
-- This migration:
--   1. Copies any rows from public."Log" into suomisf.log
--   2. Drops the stray public."Log" table

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relname = 'Log' AND n.nspname = 'public'
          AND c.relkind = 'r'
    ) THEN
        INSERT INTO suomisf.log
            (table_name, field_name, table_id, object_name, action,
             user_id, old_value, date)
        SELECT
            table_name, field_name, table_id, object_name, action,
            user_id, old_value, date::timestamptz
        FROM public."Log";

        DROP TABLE public."Log" CASCADE;
    END IF;
END;
$$;
