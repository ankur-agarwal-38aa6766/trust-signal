-- Select the intended database first. Only an administrator writes this ledger.
CREATE SCHEMA IF NOT EXISTS TRUST_SIGNAL_OPS;
CREATE TABLE IF NOT EXISTS TRUST_SIGNAL_OPS.SCHEMA_MIGRATIONS (
    VERSION NUMBER(10, 0) NOT NULL,
    FILENAME VARCHAR NOT NULL,
    CHECKSUM VARCHAR NOT NULL,
    APPLIED_AT TIMESTAMP_TZ NOT NULL,
    APPLIED_BY VARCHAR NOT NULL,
    APPLIED_ROLE VARCHAR NOT NULL
);
-- Standard-table constraints do not serialize deployers: use one initializer at a time.
