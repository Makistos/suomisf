-- Migration 010: Add notes field to shortstory table
-- Adds a free-text notes column to suomisf.shortstory.

ALTER TABLE suomisf.shortstory
    ADD COLUMN IF NOT EXISTS notes TEXT;
