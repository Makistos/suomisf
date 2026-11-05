-- Migration 046: tag pairs added by hand
--
-- Admins can link two tags as similar from the tag page. Such a pair has
-- reason 'manual'; scripts/tag_similarity.py never changes or removes it.

ALTER TABLE suomisf.tag_similarity
    DROP CONSTRAINT IF EXISTS tag_similarity_reason_check;
ALTER TABLE suomisf.tag_similarity
    ADD CONSTRAINT tag_similarity_reason_check
    CHECK (reason IN ('baseform', 'spelling', 'place', 'name', 'usage',
                      'manual'));
