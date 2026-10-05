"""Portable deterministic validation before interpretation and assessment."""

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from trust_signal.domain.aggregation import AggregationResult
from trust_signal.domain.identity import IdentityResolution
from trust_signal.domain.validation import FindingValidation, ValidationResult
from trust_signal.models import BranchResult, CaseRequest
from trust_signal.resolution.confirmed import confirmed_subject
from trust_signal.resolution.resolver import name_key


class EvidenceValidator:
    def validate(self, request: CaseRequest, branches: list[BranchResult],
                 aggregation: AggregationResult, identity: IdentityResolution | None, *,
                 now: datetime | None = None) -> ValidationResult:
        now = now or datetime.now(UTC)
        if now.utcoffset() is None:
            raise ValueError("Validation time requires a timezone.")
        try:
            subject = confirmed_subject(request, identity) if identity else None
        except ValueError:
            subject = None
        findings, duplicates = {}, set()
        membership = Counter(identifier for group in aggregation.groups for identifier in group.finding_ids)
        conflicts = {identifier for group in aggregation.groups if group.relation == "potential_conflict"
                     for identifier in group.finding_ids}
        for branch in branches:
            for finding in branch.findings:
                if finding.finding_id in findings and findings[finding.finding_id][1] != finding:
                    duplicates.add(finding.finding_id)
                findings[finding.finding_id] = (branch, finding)
        unknown_references = set(membership) - set(findings)
        result = ValidationResult(checked_at=now)
        for identifier, (branch, finding) in sorted(findings.items()):
            errors, review = [], []
            if identifier in duplicates:
                errors.append("conflicting_finding_id")
            if branch.status != "completed" or finding.branch_id != branch.branch_id:
                errors.append("invalid_branch_lineage")
            if finding.evidence_mode != "live_source":
                errors.append("fixture_not_live_evidence")
            if not finding.observation_ids or any(not item.strip() for item in finding.observation_ids):
                errors.append("missing_observation_lineage")
            elif len(set(finding.observation_ids)) != len(finding.observation_ids):
                errors.append("duplicate_observation_lineage")
            if (not finding.source_id.strip() or not finding.source_record_id
                    or not finding.source_run_id or not finding.connector_version):
                errors.append("missing_source_lineage")
            if not finding.content_hash or not re.fullmatch(r"sha256:[0-9a-f]{64}", finding.content_hash):
                errors.append("invalid_content_hash")
            try:
                url = urlparse(finding.source_url or "")
                valid_url = (url.scheme in {"https", "http"} and bool(url.hostname)
                             and not url.username and not url.password and url.port in {None, 80, 443})
            except ValueError:
                valid_url = False
            if not valid_url:
                errors.append("invalid_source_url")
            if finding.observed_at is None or finding.observed_at.utcoffset() is None:
                errors.append("missing_aware_observation_time")
            elif finding.observed_at > now + timedelta(minutes=5):
                errors.append("future_observation_time")
            if membership[identifier] != 1 or unknown_references:
                errors.append("invalid_aggregation_membership")
            if subject is None:
                review.append("identity_unconfirmed")
            elif finding.subject_id != subject.candidate_id:
                review.append("finding_attribution_unconfirmed")
            elif name_key(finding.subject) not in {name_key(name) for name in [subject.legal_name, *subject.aliases]}:
                errors.append("subject_label_conflict")
            if identifier in conflicts:
                review.append("unresolved_claim_conflict")
            review.append("claim_validation_not_configured")
            result.findings.append(FindingValidation(
                finding_id=identifier, status="rejected" if errors else "review_required",
                reason_codes=[*errors, *review], structural_checks_passed=not errors))
        if any(item.status == "rejected" for item in result.findings):
            result.status = "completed_with_gaps"
        if unknown_references:
            result.limitations.append("Aggregation contains unknown finding references.")
        return result
