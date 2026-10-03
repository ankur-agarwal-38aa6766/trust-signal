"""Deterministic comparison without discarding evidence or inferring identity."""

import re
from collections import defaultdict
from datetime import UTC
from typing import Protocol

from trust_signal.domain.aggregation import (
    AggregationResult,
    BranchCoverage,
    ClaimGroup,
    ComparisonItem,
    TimelineEntry,
)
from trust_signal.domain.identity import IdentityResolution
from trust_signal.models import BranchResult, Finding
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import name_key


class AggregationService(Protocol):
    def aggregate(self, branches: list[BranchResult],
                  identity: IdentityResolution | None = None) -> AggregationResult: ...


class EvidenceAggregator:
    def aggregate(self, branches: list[BranchResult],
                  identity: IdentityResolution | None = None) -> AggregationResult:
        findings: dict[str, Finding] = {}
        coverage = []
        for branch in sorted(branches, key=lambda b: b.branch_id):
            coverage.append(BranchCoverage(
                branch_id=branch.branch_id, status=branch.status.value,
                sources_checked=sorted(set(branch.sources_checked)),
                limitations=sorted(set(branch.limitations)), error=branch.error,
                finding_count=len(branch.findings),
            ))
            for finding in branch.findings:
                previous = findings.get(finding.finding_id)
                if previous is not None and previous != finding:
                    raise ValueError("One finding ID refers to conflicting finding contents.")
                findings[finding.finding_id] = finding

        grouped = defaultdict(list)
        for finding in findings.values():
            subject = ("id:" + finding.subject_id if finding.subject_id else
                       "name:" + name_key(finding.subject))
            effective = (finding.effective_at.astimezone(UTC).isoformat()
                         if finding.effective_at else "")
            event_time = (finding.event_at.astimezone(UTC).isoformat()
                          if finding.event_at else "")
            key = (subject, finding.claim_type, finding.claim_key or "",
                   finding.event_id or "", effective, event_time,
                   finding.evidence_mode.value, finding.claim_cardinality)
            grouped[key].append(finding)

        result = AggregationResult(coverage=coverage)
        if identity is None or identity.status != "resolved":
            result.limitations.append("Identity is not resolved; groups do not confirm attribution.")
        if any(c.status != "completed" for c in coverage):
            result.limitations.append("Some branches failed or were skipped; coverage is incomplete.")
        for key, members in sorted(grouped.items()):
            members.sort(key=lambda f: f.finding_id)
            subject, claim_type, claim_key, event_id, effective, event_time, _mode, cardinality = key
            group_id = stable_id("group", *key)
            evidence = defaultdict(list)
            for item in members:
                # Same response bytes and claim are repeated evidence, even across publishers.
                value = item.claim_value if claim_key and item.claim_value is not None else item.claim
                fingerprint = ((item.content_hash, value, item.procedural_status)
                               if item.content_hash and re.fullmatch(r"sha256:[0-9a-f]{64}",
                                                                     item.content_hash) else
                               ("finding", item.finding_id))
                evidence[fingerprint].append(item.finding_id)
            duplicates = sorted(sorted(ids) for ids in evidence.values() if len(ids) > 1)
            values = {f.claim_value for f in members if f.claim_value is not None}
            if claim_key and cardinality == "single" and len(values) > 1:
                relation = "potential_conflict"
            elif duplicates and len(evidence) == 1:
                relation = "duplicate_evidence"
            elif claim_key and cardinality == "multiple" and len(values) > 1:
                relation = "combined_members"
            elif claim_key and len(values) == 1 and len(members) > 1 and all(
                f.claim_value is not None for f in members
            ):
                relation = "consistent_claims"
            elif len({f.branch_id for f in members}) > 1:
                relation = "same_claim_type_across_branches"
            elif len(members) > 1:
                relation = "unstructured_claims"
            else:
                relation = "single_finding"
            group = ClaimGroup(
                group_id=group_id, subject_key=subject, claim_type=claim_type,
                claim_key=claim_key or None, event_id=event_id or None,
                claim_cardinality=cardinality,
                event_at=members[0].event_at if event_time else None,
                effective_at=members[0].effective_at if effective else None,
                finding_ids=[f.finding_id for f in members],
                source_ids=sorted({f.source_id for f in members}),
                branch_ids=sorted({f.branch_id for f in members}), values=sorted(values),
                observation_ids=sorted({o for f in members for o in f.observation_ids}),
                duplicate_sets=duplicates, distinct_evidence_count=len(evidence), relation=relation,
                identity_confirmed=bool(identity and identity.status == "resolved" and
                                        subject == "id:" + str(identity.selected_candidate_id) and
                                        any(m.candidate.candidate_id == identity.selected_candidate_id
                                            and m.eligible_for_attribution for m in identity.matches)),
            )
            result.groups.append(group)
            result.comparison_board.append(ComparisonItem(
                finding_ids=group.finding_ids, relation=relation,
                summary=(f"{len(members)} finding(s) for {claim_type}; "
                         f"{len(evidence)} distinct evidence item(s). "
                         "Inspect source records and identity attribution before assessment."),
            ))
            dated = defaultdict(list)
            for item in members:
                if item.event_at is not None:
                    dated[item.event_at.astimezone(UTC)].append(item.finding_id)
            result.timeline.extend(TimelineEntry(event_at=date, finding_ids=sorted(ids),
                                                 group_id=group_id)
                                   for date, ids in sorted(dated.items()))
        result.timeline.sort(key=lambda t: (t.event_at, t.group_id))
        if any(g.subject_key.startswith("name:") for g in result.groups):
            result.limitations.append("Name-based grouping is provisional and does not merge entities.")
        result.limitations.append("Distinct source IDs do not establish independent corroboration.")
        return result
