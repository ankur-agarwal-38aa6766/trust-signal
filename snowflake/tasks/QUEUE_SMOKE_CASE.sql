-- Use an isolated DEV database and an authorized intake/admin role with INSERT.
-- The task runtime role deliberately has no request-submission privilege.
-- Confirm the existing queue is empty before executing the one-case smoke graph.
INSERT INTO TRUST_SIGNAL_CORE.CASE_REQUESTS (
    REQUEST_ID, CASE_ID, TENANT_ID, REQUEST_STATUS, IDEMPOTENCY_KEY,
    REQUESTED_BY, REQUESTED_AT, REQUEST_PAYLOAD
)
SELECT 'workflow_smoke_microsoft_v1', 'case_workflow_smoke_microsoft_v1',
       'demo', 'queued', 'workflow_smoke_microsoft_v1', CURRENT_USER(), CURRENT_TIMESTAMP(),
       PARSE_JSON('{
         "schema_version": "1",
         "party": {
           "legal_name": "Microsoft Corporation",
           "lei": "INR2EJN1ERAN0W5ZP974",
           "jurisdiction": "US"
         },
         "source_mode": "gleif_live"
       }')
WHERE NOT EXISTS (
    SELECT 1 FROM TRUST_SIGNAL_CORE.CASE_REQUESTS
    WHERE REQUEST_ID = 'workflow_smoke_microsoft_v1' AND TENANT_ID = 'demo'
);
