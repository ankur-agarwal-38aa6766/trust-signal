"""Durable workflow repository with atomic claims and append-only stage attempts."""

import json
import re
from contextlib import contextmanager

from trust_signal.domain.workflow import (
    StageAttempt,
    WorkflowInputFailure,
    WorkflowRun,
    WorkflowStage,
)
from trust_signal.ingestion.observation import sql_literal
from trust_signal.models import CaseResult
from trust_signal.persistence.contracts import ObservationWriteError, SqlExecutor
from trust_signal.persistence.source_runs import _details_sql
from trust_signal.resolution.evidence import stable_id


class WorkflowWriteError(ObservationWriteError):
    """Workflow state could not be reconciled safely."""


class SnowflakeWorkflowStore:
    def __init__(self, executor: SqlExecutor, database: str):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", database):
            raise ValueError("Invalid Snowflake database identifier.")
        self.executor = executor
        self.runs = f"{database}.TRUST_SIGNAL_OPS.CASE_RUNS"
        self.attempts = f"{database}.TRUST_SIGNAL_OPS.STAGE_ATTEMPTS"
        self.requests = f"{database}.TRUST_SIGNAL_CORE.CASE_REQUESTS"

    @contextmanager
    def _transaction(self):
        self.executor.execute("BEGIN TRANSACTION")
        try:
            yield
            self.executor.execute("COMMIT")
        except Exception:
            self.executor.execute("ROLLBACK")
            raise

    def claim(self, graph_run_id: str) -> str:
        if not graph_run_id.strip():
            raise ValueError("A graph run ID is required.")
        existing = self.executor.execute(
            f"SELECT RUN_ID FROM {self.runs} WHERE GRAPH_RUN_ID = {sql_literal(graph_run_id)}")
        if existing:
            if len(existing) != 1:
                raise WorkflowWriteError("Graph run maps to multiple case runs.")
            return existing[0]["RUN_ID"]
        with self._transaction():
            rows = self.executor.execute(f"""SELECT REQUEST_ID, CASE_ID, TENANT_ID,
TO_JSON(REQUEST_PAYLOAD) AS PAYLOAD_JSON FROM {self.requests}
WHERE REQUEST_STATUS = 'queued' ORDER BY REQUESTED_AT, REQUEST_ID LIMIT 1""")
            if not rows:
                return "NONE"
            row = rows[0]
            request_id = row["REQUEST_ID"]
            run_id = stable_id("workflow", graph_run_id, request_id)
            changed = self.executor.execute(f"""UPDATE {self.requests}
SET REQUEST_STATUS = 'running', CLAIMED_AT = CURRENT_TIMESTAMP()
WHERE REQUEST_ID = {sql_literal(request_id)} AND TENANT_ID = {sql_literal(row['TENANT_ID'])}
AND REQUEST_STATUS = 'queued'""")
            if sum(r.get("number of rows updated", 0) for r in changed) != 1:
                raise WorkflowWriteError("Queue claim lost ownership or matched duplicate requests.")
            self.executor.execute(f"""INSERT INTO {self.runs}
(RUN_ID, GRAPH_RUN_ID, REQUEST_ID, CASE_ID, TENANT_ID, RUN_STATUS, REQUEST_PAYLOAD, STARTED_AT)
SELECT {sql_literal(run_id)}, {sql_literal(graph_run_id)}, {sql_literal(request_id)},
{sql_literal(row['CASE_ID'])}, {sql_literal(row['TENANT_ID'])}, 'running',
{_details_sql(json.loads(row['PAYLOAD_JSON']))}, CURRENT_TIMESTAMP()""")
            run = self.load(run_id)
            if run.graph_run_id != graph_run_id or run.request_id != request_id:
                raise WorkflowWriteError("Claimed run readback mismatch.")
        return run_id

    def load(self, run_id: str) -> WorkflowRun:
        rows = self.executor.execute(f"""SELECT RUN_ID, GRAPH_RUN_ID, REQUEST_ID, CASE_ID,
TENANT_ID, RUN_STATUS, TO_JSON(REQUEST_PAYLOAD) AS PAYLOAD_JSON
FROM {self.runs} WHERE RUN_ID = {sql_literal(run_id)}""")
        if len(rows) != 1:
            raise WorkflowWriteError("Expected exactly one workflow run.")
        row = rows[0]
        return WorkflowRun(run_id=row["RUN_ID"], graph_run_id=row["GRAPH_RUN_ID"],
                           request_id=row["REQUEST_ID"], case_id=row["CASE_ID"],
                           tenant_id=row["TENANT_ID"], status=row["RUN_STATUS"],
                           request_payload=json.loads(row["PAYLOAD_JSON"]))

    def latest(self, run_id: str, stage: WorkflowStage) -> StageAttempt | None:
        rows = self.executor.execute(f"""SELECT ATTEMPT_ID, RUN_ID, STAGE, ATTEMPT,
STAGE_STATUS, TO_JSON(OUTPUT) AS OUTPUT_JSON, ERROR_CATEGORY
FROM {self.attempts} WHERE RUN_ID = {sql_literal(run_id)} AND STAGE = {sql_literal(stage.value)}
QUALIFY DENSE_RANK() OVER (ORDER BY ATTEMPT DESC) = 1""")
        if not rows:
            return None
        if len(rows) != 1:
            raise WorkflowWriteError("Latest stage attempt is duplicated.")
        row = rows[0]
        return StageAttempt(attempt_id=row["ATTEMPT_ID"], run_id=row["RUN_ID"], stage=row["STAGE"],
                            attempt=row["ATTEMPT"], status=row["STAGE_STATUS"],
                            output=json.loads(row["OUTPUT_JSON"]) if row["OUTPUT_JSON"] else None,
                            error_category=row["ERROR_CATEGORY"])

    def start(self, run_id: str, stage: WorkflowStage) -> StageAttempt:
        previous = self.latest(run_id, stage)
        attempt = StageAttempt(attempt_id=stable_id("attempt", run_id, stage.value,
                                                   str(previous.attempt + 1 if previous else 1)),
                               run_id=run_id, stage=stage,
                               attempt=previous.attempt + 1 if previous else 1, status="running")
        with self._transaction():
            if previous and previous.status == "running":
                self.fail(previous, "InterruptedAttempt")
            self.executor.execute(f"""INSERT INTO {self.attempts}
(ATTEMPT_ID, RUN_ID, STAGE, ATTEMPT, STAGE_STATUS, STARTED_AT)
SELECT {sql_literal(attempt.attempt_id)}, {sql_literal(run_id)}, {sql_literal(stage.value)},
{attempt.attempt}, 'running', CURRENT_TIMESTAMP()""")
            if self.latest(run_id, stage) != attempt:
                raise WorkflowWriteError("Stage claim could not be verified.")
        return attempt

    def complete(self, attempt: StageAttempt, output: dict, status: str) -> None:
        if status not in {"succeeded", "completed_with_gaps", "skipped"}:
            raise ValueError("Invalid completed stage status.")
        with self._transaction():
            self.executor.execute(f"""UPDATE {self.attempts}
SET STAGE_STATUS = {sql_literal(status)}, OUTPUT = {_details_sql(output)},
ERROR_CATEGORY = NULL, COMPLETED_AT = CURRENT_TIMESTAMP()
WHERE ATTEMPT_ID = {sql_literal(attempt.attempt_id)} AND STAGE_STATUS = 'running'""")
            saved = self.latest(attempt.run_id, attempt.stage)
            if (not saved or saved.attempt_id != attempt.attempt_id or saved.status != status
                    or saved.output != output):
                raise WorkflowWriteError("Completed stage output failed readback verification.")

    def fail(self, attempt: StageAttempt, error_category: str) -> None:
        self.executor.execute(f"""UPDATE {self.attempts}
SET STAGE_STATUS = 'failed', ERROR_CATEGORY = {sql_literal(error_category)},
COMPLETED_AT = CURRENT_TIMESTAMP()
WHERE ATTEMPT_ID = {sql_literal(attempt.attempt_id)} AND STAGE_STATUS = 'running'""")

    def finish(self, run_id: str, result: CaseResult | WorkflowInputFailure) -> None:
        run = self.load(run_id)
        if result.case_id != run.case_id:
            raise ValueError("Result belongs to another case.")
        payload = result.model_dump(mode="json")
        status = str(result.status)
        with self._transaction():
            self.executor.execute(f"""UPDATE {self.runs}
SET RUN_STATUS = {sql_literal(status)}, RESULT = {_details_sql(payload)},
ERROR_CATEGORY = NULL, COMPLETED_AT = CURRENT_TIMESTAMP()
WHERE RUN_ID = {sql_literal(run_id)} AND RUN_STATUS IN ('running', 'retryable')""")
            self.executor.execute(f"""UPDATE {self.requests}
SET REQUEST_STATUS = {sql_literal(status)}, COMPLETED_AT = CURRENT_TIMESTAMP(),
ERROR_CATEGORY = NULL, ERROR_MESSAGE = NULL
WHERE REQUEST_ID = {sql_literal(run.request_id)} AND TENANT_ID = {sql_literal(run.tenant_id)}
AND REQUEST_STATUS IN ('running', 'retryable')""")
            rows = self.executor.execute(f"""SELECT r.RUN_STATUS, TO_JSON(r.RESULT) AS RESULT_JSON,
q.REQUEST_STATUS FROM {self.runs} r JOIN {self.requests} q
ON r.REQUEST_ID = q.REQUEST_ID AND r.TENANT_ID = q.TENANT_ID
WHERE r.RUN_ID = {sql_literal(run_id)}""")
            if (len(rows) != 1 or rows[0]["RUN_STATUS"] != status
                    or rows[0]["REQUEST_STATUS"] != status
                    or json.loads(rows[0]["RESULT_JSON"]) != payload):
                raise WorkflowWriteError("Terminal case result failed readback verification.")

    def finalize(self, graph_run_id: str) -> None:
        with self._transaction():
            self.executor.execute(f"""UPDATE {self.attempts} s
SET STAGE_STATUS = 'failed', ERROR_CATEGORY = 'InterruptedAttempt', COMPLETED_AT = CURRENT_TIMESTAMP()
FROM {self.runs} r WHERE s.RUN_ID = r.RUN_ID
AND r.GRAPH_RUN_ID = {sql_literal(graph_run_id)} AND s.STAGE_STATUS = 'running'""")
            self.executor.execute(f"""UPDATE {self.requests} q
SET REQUEST_STATUS = 'retryable', ERROR_CATEGORY = 'WorkflowInterrupted'
FROM {self.runs} r WHERE q.REQUEST_ID = r.REQUEST_ID AND q.TENANT_ID = r.TENANT_ID
AND r.GRAPH_RUN_ID = {sql_literal(graph_run_id)} AND r.RUN_STATUS IN ('running', 'retryable')
AND q.REQUEST_STATUS = 'running'""")
            self.executor.execute(f"""UPDATE {self.runs}
SET RUN_STATUS = 'retryable', ERROR_CATEGORY = 'WorkflowInterrupted'
WHERE GRAPH_RUN_ID = {sql_literal(graph_run_id)} AND RUN_STATUS = 'running'""")

    def requeue(self, run_id: str) -> None:
        run = self.load(run_id)
        if run.status != "retryable":
            raise ValueError("Only interrupted runs can be requeued.")
        with self._transaction():
            changed = self.executor.execute(f"""UPDATE {self.requests} SET REQUEST_STATUS = 'queued',
CLAIMED_AT = NULL, COMPLETED_AT = NULL, ERROR_CATEGORY = NULL, ERROR_MESSAGE = NULL
WHERE REQUEST_ID = {sql_literal(run.request_id)} AND TENANT_ID = {sql_literal(run.tenant_id)}
AND REQUEST_STATUS = 'retryable'""")
            if sum(r.get("number of rows updated", 0) for r in changed) != 1:
                raise WorkflowWriteError("Request is no longer available for recovery.")
