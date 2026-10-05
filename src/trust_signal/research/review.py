"""Portable review service with a transactional local adapter; no external actions."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from trust_signal.domain.review import ReviewCommand, ReviewerContext, ReviewReceipt
from trust_signal.models import CaseResult


def snapshot_hash(case: CaseResult) -> str:
    payload = json.dumps(case.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


class ReviewConflict(ValueError):
    """The version, snapshot or idempotency payload conflicts with durable state."""


class ReviewStore(Protocol):
    def register(self, tenant_id: str, case: CaseResult) -> str: ...
    def apply(self, actor: ReviewerContext, command: ReviewCommand) -> ReviewReceipt: ...
    def history(self, tenant_id: str, case_id: str) -> list[ReviewReceipt]: ...


class ReviewService:
    def __init__(self, store: ReviewStore):
        self.store = store

    @staticmethod
    def _authorize(actor):
        if actor.role not in {"reviewer", "supervisor"}:
            raise PermissionError("Reviewer authority is required.")

    def register(self, actor: ReviewerContext, case: CaseResult) -> str:
        self._authorize(actor)
        return self.store.register(actor.tenant_id, case)

    def decide(self, actor: ReviewerContext, command: ReviewCommand) -> ReviewReceipt:
        self._authorize(actor)
        if command.action == "reopen" and actor.role != "supervisor":
            raise PermissionError("Only a supervisor can reopen a rejected case.")
        return self.store.apply(actor, command)

    def history(self, actor: ReviewerContext, case_id: str) -> list[ReviewReceipt]:
        self._authorize(actor)
        return self.store.history(actor.tenant_id, case_id)


class SqliteReviewStore:
    """Development-only durable adapter; production identity/RBAC is not provided."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS review_cases (
                    tenant_id TEXT NOT NULL, case_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
                    snapshot TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL DEFAULT 'awaiting_review', PRIMARY KEY (tenant_id, case_id));
                CREATE TABLE IF NOT EXISTS review_events (
                    tenant_id TEXT NOT NULL, case_id TEXT NOT NULL, request_id TEXT NOT NULL,
                    version INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, case_id, request_id), UNIQUE (tenant_id, case_id, version));
            """)
        if new:
            self.path.chmod(0o600)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def register(self, tenant_id, case):
        digest = snapshot_hash(case)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT snapshot_hash FROM review_cases WHERE tenant_id=? AND case_id=?",
                             (tenant_id, case.case_id)).fetchone()
            if row:
                if row["snapshot_hash"] != digest:
                    raise ReviewConflict("Research snapshot is immutable; register a new case version.")
            else:
                db.execute("INSERT INTO review_cases (tenant_id,case_id,snapshot_hash,snapshot) VALUES (?,?,?,?)",
                           (tenant_id, case.case_id, digest, case.model_dump_json()))
        return digest

    def apply(self, actor, command):
        # The adapter also enforces authorization, even when called without the service.
        ReviewService._authorize(actor)
        if command.action == "reopen" and actor.role != "supervisor":
            raise PermissionError("Supervisor authority is required.")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            scope = (actor.tenant_id, command.case_id)
            previous = db.execute("SELECT payload FROM review_events WHERE tenant_id=? AND case_id=? AND request_id=?",
                                  (*scope, command.request_id)).fetchone()
            if previous:
                receipt = ReviewReceipt.model_validate_json(previous["payload"])
                if (receipt.command != command or receipt.reviewer_id != actor.user_id
                        or receipt.reviewer_role != actor.role):
                    raise ReviewConflict("Idempotency key was used with another command or reviewer.")
                return receipt
            row = db.execute("SELECT * FROM review_cases WHERE tenant_id=? AND case_id=?", scope).fetchone()
            if row is None:
                raise LookupError("Review case not found in this tenant.")
            if row["version"] != command.expected_version or row["snapshot_hash"] != command.snapshot_hash:
                raise ReviewConflict("Stale review version or research snapshot.")
            if row["state"] == "rejected" and command.action != "reopen":
                raise ReviewConflict("Rejected case requires a supervisor reopen.")
            if command.action == "reopen" and row["state"] != "rejected":
                raise ReviewConflict("Only a rejected case can be reopened.")
            case = CaseResult.model_validate_json(row["snapshot"])
            ids = {finding.finding_id for branch in case.branches for finding in branch.findings}
            if len(set(command.finding_ids)) != len(command.finding_ids) or set(command.finding_ids) - ids:
                raise ValueError("Decision references duplicate or unknown findings.")
            if command.action == "request_details" and (not command.questions or any(not q.strip() for q in command.questions)):
                raise ValueError("Request-details requires explicit nonempty questions.")
            if command.action != "request_details" and command.questions:
                raise ValueError("Questions are only valid for request-details.")
            if command.action == "reject":
                if not command.acknowledge_limitations or not command.finding_ids:
                    raise ValueError("Rejection requires evidence references and acknowledgment of limitations.")
                if case.validation is None:
                    raise ValueError("Evidence validation is required before recording rejection.")
                valid = {item.finding_id for item in case.validation.findings if item.structural_checks_passed}
                if not set(command.finding_ids) <= valid:
                    raise ValueError("Rejection references structurally invalid evidence.")
            state = {"review": "awaiting_review", "request_details": "details_requested",
                     "reject": "rejected", "reopen": "awaiting_review"}[command.action]
            receipt = ReviewReceipt(event_id="review_" + uuid4().hex, request_id=command.request_id,
                                    case_id=command.case_id, snapshot_hash=command.snapshot_hash,
                                    version=row["version"] + 1, state=state, reviewer_id=actor.user_id,
                                    reviewer_role=actor.role, recorded_at=datetime.now(UTC), command=command)
            db.execute("INSERT INTO review_events VALUES (?,?,?,?,?)",
                       (*scope, command.request_id, receipt.version, receipt.model_dump_json()))
            db.execute("UPDATE review_cases SET version=?,state=? WHERE tenant_id=? AND case_id=?",
                       (receipt.version, state, *scope))
            return receipt

    def history(self, tenant_id, case_id):
        with closing(self._connect()) as db:
            rows = db.execute("SELECT payload FROM review_events WHERE tenant_id=? AND case_id=? ORDER BY version",
                              (tenant_id, case_id)).fetchall()
        return [ReviewReceipt.model_validate_json(row["payload"]) for row in rows]
