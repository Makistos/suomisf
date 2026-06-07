import psycopg2

conn = psycopg2.connect(host='127.0.0.1', dbname='suomisf', user='mep', password='tsw80yofiv71mwqb')
conn.autocommit = True
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS suomisf.antikvaari_price CASCADE')
cur.execute('''
CREATE TABLE suomisf.antikvaari_price (
    id                          SERIAL PRIMARY KEY,
    work_id                     INTEGER NOT NULL REFERENCES suomisf.work(id),
    antikvaari_book_id          VARCHAR(30) NOT NULL,
    antikvaari_product_id       VARCHAR(30) NOT NULL,
    antikvaari_product_year     INTEGER,
    antikvaari_product_binding  VARCHAR(100),
    antikvaari_product_version  INTEGER,
    date_listed                 DATE,
    date_fetched                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    condition                   VARCHAR(5) NOT NULL,
    is_library_discard          BOOLEAN NOT NULL DEFAULT FALSE,
    has_markings                BOOLEAN NOT NULL DEFAULT FALSE,
    price                       NUMERIC(8, 2) NOT NULL
)
''')
cur.execute('CREATE INDEX ix_antikvaari_price_work_id ON suomisf.antikvaari_price (work_id)')
cur.execute('CREATE INDEX ix_antikvaari_price_book_id ON suomisf.antikvaari_price (antikvaari_book_id)')

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='suomisf' AND table_name='antikvaari_price' ORDER BY ordinal_position")
print('antikvaari_price columns:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='suomisf' AND table_name='antikvaari_work_product' ORDER BY ordinal_position")
print('antikvaari_work_product columns:', [r[0] for r in cur.fetchall()])

conn.close()
print('Migration complete')
