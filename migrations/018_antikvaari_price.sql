-- Migration 018: Antikvaari pricing tables
--
-- antikvaari_work_product: maps our works to Antikvaari product IDs for reuse.
-- antikvaari_price: append-only scraped price history per physical book copy,
--   keyed by edition. Prices are never updated; each fetch creates new rows.
--   last_updated: when the Antikvaari listing was last updated on their side.
--   date_fetched:  when we ran the price check and inserted this row.

CREATE TABLE suomisf.antikvaari_work_product (
    id                      SERIAL PRIMARY KEY,
    work_id                 INTEGER NOT NULL REFERENCES suomisf.work(id),
    antikvaari_product_id   VARCHAR(30) NOT NULL,
    added                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (work_id, antikvaari_product_id)
);

CREATE INDEX ix_antikvaari_work_product_work_id
    ON suomisf.antikvaari_work_product (work_id);

CREATE TABLE suomisf.antikvaari_price (
    id                          SERIAL PRIMARY KEY,
    edition_id                  INTEGER NOT NULL REFERENCES suomisf.edition(id),
    antikvaari_book_id          VARCHAR(30) NOT NULL,
    antikvaari_product_id       VARCHAR(30) NOT NULL,
    antikvaari_product_year     INTEGER,
    antikvaari_product_binding  VARCHAR(100),
    antikvaari_product_version  INTEGER,
    date_listed                 DATE,
    last_updated                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_fetched                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    condition                   VARCHAR(5) NOT NULL,
    is_library_discard          BOOLEAN NOT NULL DEFAULT FALSE,
    has_markings                BOOLEAN NOT NULL DEFAULT FALSE,
    missing_dust_cover          BOOLEAN NOT NULL DEFAULT FALSE,
    price                       NUMERIC(8, 2) NOT NULL
);

CREATE INDEX ix_antikvaari_price_edition_id
    ON suomisf.antikvaari_price (edition_id);
CREATE INDEX ix_antikvaari_price_book_id
    ON suomisf.antikvaari_price (antikvaari_book_id);
