-- Migration 019: Fix antikvaari_price to match migration 018 final schema
--
-- In dev the table was created from an earlier draft of 018 which had:
--   - a UNIQUE constraint on antikvaari_book_id (prices must be append-only)
--   - no missing_dust_cover column
--   - no date_fetched column
--
-- This migration is idempotent: on a production DB where 018 created the
-- table correctly, all blocks are no-ops.

DO $$
DECLARE
    v_constraint TEXT;
BEGIN
    -- Drop any UNIQUE constraint on antikvaari_book_id
    SELECT tc.constraint_name INTO v_constraint
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name
     AND tc.table_schema    = ccu.table_schema
    WHERE tc.table_schema   = 'suomisf'
      AND tc.table_name     = 'antikvaari_price'
      AND tc.constraint_type = 'UNIQUE'
      AND ccu.column_name   = 'antikvaari_book_id'
    LIMIT 1;

    IF v_constraint IS NOT NULL THEN
        EXECUTE 'ALTER TABLE suomisf.antikvaari_price DROP CONSTRAINT ' || v_constraint;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'suomisf'
          AND table_name   = 'antikvaari_price'
          AND column_name  = 'missing_dust_cover'
    ) THEN
        ALTER TABLE suomisf.antikvaari_price
            ADD COLUMN missing_dust_cover BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'suomisf'
          AND table_name   = 'antikvaari_price'
          AND column_name  = 'date_fetched'
    ) THEN
        ALTER TABLE suomisf.antikvaari_price
            ADD COLUMN date_fetched TIMESTAMPTZ NOT NULL DEFAULT NOW();
    END IF;
END;
$$;
