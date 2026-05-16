CREATE TABLE suomisf.ip_location (
    ip      VARCHAR(45) PRIMARY KEY,
    city    VARCHAR(100),
    country VARCHAR(2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
GRANT SELECT, INSERT, UPDATE ON suomisf.ip_location TO mep;
