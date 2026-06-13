-- Migration 024: Price source tracking
--
-- Adds a price_source lookup table and links antikvaari_price rows to it.
-- Makes antikvaari_book_id and antikvaari_product_id nullable so that
-- manually entered prices (without a scraper book ID) can be stored.

CREATE TABLE suomisf.price_source (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO suomisf.price_source (name) VALUES
    ('Antikvaari'),
    ('Antikvariaatti'),
    ('Antikka'),
    ('Huuto.net');

ALTER TABLE suomisf.antikvaari_price
    ADD COLUMN source_id INTEGER REFERENCES suomisf.price_source(id);

UPDATE suomisf.antikvaari_price
    SET source_id = (SELECT id FROM suomisf.price_source WHERE name = 'Antikvaari');

ALTER TABLE suomisf.antikvaari_price
    ALTER COLUMN source_id SET NOT NULL,
    ALTER COLUMN antikvaari_book_id DROP NOT NULL,
    ALTER COLUMN antikvaari_product_id DROP NOT NULL;
