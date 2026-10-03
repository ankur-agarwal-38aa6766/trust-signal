-- Select the target database; apply after V001 and before using shared ingestion.
ALTER TABLE TRUST_SIGNAL_RAW.SOURCE_OBSERVATIONS
    ADD COLUMN IF NOT EXISTS RAW_RESPONSE_TEXT VARCHAR;
-- Old observations require replay of their original bundles to populate this column.
