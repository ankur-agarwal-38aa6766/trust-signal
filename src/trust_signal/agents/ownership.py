"""Bounded, evidence-backed accounting relationships and organizational roles."""

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from trust_signal.connectors.base import EntityRecord, OrganizationRole
from trust_signal.connectors.registry import SourceRequest
from trust_signal.domain.identity import IdentityCandidate, IdentityResolution
from trust_signal.domain.ownership import OwnershipRecord, OwnershipResearchResult, ResearchCoverage
from trust_signal.models import BranchResult, CaseRequest, Finding, PartyInput
from trust_signal.research.provider import ResearchDataset, ResearchProvider
from trust_signal.resolution.confirmed import confirmed_subject
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import EntityResolver

GLEIF = "gleif_lei_api"
NORWAY = "no_bronnoysund_enhetsregisteret"


class OwnershipSpecialist:
    def __init__(self, provider: ResearchProvider, *, norway_organization_number: str | None = None,
                 max_pages: int = 5, max_observation_age: timedelta = timedelta(hours=24),
                 clock: Callable[[], datetime] | None = None):
        if norway_organization_number is not None and not re.fullmatch(r"[0-9]{9}", norway_organization_number):
            raise ValueError("Norwegian organization number must contain exactly 9 digits.")
        if not 1 <= max_pages <= 100 or max_observation_age <= timedelta(0):
            raise ValueError("Bounded pagination and positive freshness are required.")
        self.provider = provider
        self.number = norway_organization_number
        self.max_pages = max_pages
        self.max_age = max_observation_age
        self.clock = clock or (lambda: datetime.now(UTC))

    def __call__(self, request: CaseRequest, resolution: IdentityResolution) -> BranchResult:
        subject = confirmed_subject(request, resolution)
        now = self.clock()
        if now.utcoffset() is None:
            raise ValueError("Research time requires a timezone.")
        coverage = []
        records = []
        if subject.lei:
            query = SourceRequest(source_id=GLEIF, operation="relationships", value=subject.lei,
                                  max_pages=self.max_pages)
            dataset = self._load(query, now)
            coverage.append(dataset.coverage)
            if self._usable(dataset):
                try:
                    records.extend(self._gleif(dataset, subject))
                except (ValueError, KeyError, TypeError, AttributeError):
                    self._invalid(dataset)
        else:
            coverage.append(ResearchCoverage(source_id=GLEIF, operation="relationships",
                                              coverage="not_applicable", limitations=["Confirmed identity has no LEI."]))
        scoped_norway = (subject.registration_authority == NORWAY and subject.jurisdiction == "NO"
                         and subject.registration_id is not None)
        number = self.number or (subject.registration_id if scoped_norway else None)
        if number:
            query = SourceRequest(source_id=NORWAY, operation="lookup", value=number)
            lookup = self._load(query, now)
            coverage.append(lookup.coverage)
            if self._usable(lookup):
                try:
                    attribution, lookup_ids = self._norway_identity(lookup, subject, number)
                except (ValueError, KeyError, TypeError, AttributeError):
                    self._invalid(lookup)
                else:
                    roles = self._load(SourceRequest(source_id=NORWAY, operation="roles", value=number), now)
                    coverage.append(roles.coverage)
                    if self._usable(roles):
                        try:
                            records.extend(self._roles(roles, lookup, number, attribution, lookup_ids))
                        except (ValueError, KeyError, TypeError, AttributeError):
                            self._invalid(roles)
        else:
            coverage.append(ResearchCoverage(
                source_id=NORWAY, operation="roles", coverage="not_applicable",
                limitations=["No confirmed Norwegian registration scope or explicit organization-number hint."]))
        limitations = [
            "GLEIF relationships are accounting consolidation, not beneficial ownership or ownership percentages.",
            "Related entities and role holders are not independently resolved or sanctions-screened.",
            "Reporting exceptions do not prove absence of a parent or imply fraud.",
            "Norway roles are registry snapshots; deregistered roles are historical, not current appointments.",
            "This research does not compute a risk score or authorize a decision.",
        ]
        for item in coverage:
            limitations.extend(f"{item.source_id}/{item.operation}: {text}" for text in item.limitations)
            if item.coverage != "available":
                limitations.append(f"{item.source_id}/{item.operation}: coverage {item.coverage}.")
        if any(record.attribution == "pending" for record in records):
            limitations.append("Norway name-based identity linkage requires analyst confirmation.")
        research = OwnershipResearchResult(
            case_id=request.case_id, subject_id=subject.candidate_id,
            identity_observation_ids=subject.observation_ids, checked_at=now,
            coverage=coverage, records=records, limitations=limitations)
        usable = any(item.coverage in {"available", "partial", "no_matches"} for item in coverage)
        return BranchResult(
            branch_id="ownership", status="completed" if usable else "failed",
            findings=[self._finding(record, subject) for record in records], ownership_research=research,
            sources_checked=sorted({item.source_id for item in coverage if item.coverage != "not_applicable"}),
            limitations=limitations, error=None if usable else "No usable ownership or leadership research.")

    @staticmethod
    def _usable(dataset):
        return dataset.coverage.coverage in {"available", "partial", "no_matches"}

    def _load(self, query, now):
        try:
            dataset = self.provider.load(query)
            if (dataset.coverage.source_id != query.source_id
                    or dataset.coverage.operation != query.operation):
                raise ValueError("Provider returned another research operation.")
            if self._usable(dataset):
                if not dataset.evidence or not dataset.coverage.source_run_id:
                    raise ValueError("Missing persisted research evidence.")
                if any(now - item.observed_at > self.max_age or item.observed_at > now + timedelta(minutes=5)
                       for item in dataset.evidence.values()):
                    dataset.coverage.coverage = "stale"
                    dataset.coverage.limitations.append("Stale or future-dated retrieval evidence; refresh required.")
            return dataset
        except Exception as exc:  # noqa: BLE001 - preserve other research without exposing secrets
            return ResearchDataset(ResearchCoverage(
                source_id=query.source_id, operation=query.operation, coverage="failed",
                error_category=type(exc).__name__))

    @staticmethod
    def _invalid(dataset):
        dataset.coverage.coverage = "failed"
        dataset.coverage.error_category = "InvalidResearchRecord"
        dataset.coverage.limitations.append("Record identity, relationship direction or schema failed validation; withheld.")

    @staticmethod
    def _evidence(dataset, record):
        ids = record["observation_ids"]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Missing or duplicate record evidence.")
        return [dataset.evidence[key] for key in ids]

    def _record(self, dataset, record, kind, attribution, details, *, evidence=None):
        evidence = evidence or self._evidence(dataset, record)
        identifier = record["source_record_id"]
        if not identifier:
            raise ValueError("Missing source record identity.")
        return OwnershipRecord(
            record_id=stable_id("ownership", "ownership-0.1", dataset.coverage.source_id,
                                identifier, kind, attribution, *sorted(item.observation_id for item in evidence)),
            source_id=dataset.coverage.source_id, source_record_id=identifier, kind=kind,
            attribution=attribution, details=details, source_run_id=dataset.coverage.source_run_id,
            evidence=evidence)

    def _gleif(self, dataset, subject):
        identities = [record for record in dataset.records if "direction" not in record]
        if len(identities) != 1:
            raise ValueError("Relationship research must include the queried legal identity.")
        entity = EntityRecord.model_validate({key: value for key, value in identities[0].items()
                                            if key != "observation_ids"})
        self._evidence(dataset, identities[0])
        if (entity.source_id != GLEIF or entity.lei != subject.lei
                or entity.legal_name not in [subject.legal_name, *subject.aliases]):
            raise ValueError("GLEIF identity changed; reconcile before research.")
        output = []
        seen = set()
        for record in dataset.records:
            if "direction" not in record:
                continue
            direction, kind, attributes = record["direction"], record["record_type"], record["attributes"]
            key = (direction, kind, record["source_record_id"])
            if key in seen:
                raise ValueError("Duplicate relationship record.")
            seen.add(key)
            if direction not in {"direct-parent", "ultimate-parent", "direct-children"}:
                raise ValueError("Unsupported relationship direction.")
            evidence = self._evidence(dataset, record)
            if kind == "reporting-exceptions":
                reasons = (attributes["exceptionReasons"] if "exceptionReasons" in attributes
                           else [attributes["reason"]])
                expected_category = ("DIRECT_ACCOUNTING_CONSOLIDATION_PARENT" if direction == "direct-parent"
                                     else "ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT")
                if (direction == "direct-children" or not isinstance(reasons, list) or not reasons
                        or any(not isinstance(reason, str) or not reason for reason in reasons)
                        or attributes.get("category", expected_category) != expected_category):
                    raise ValueError("Invalid parent reporting exception.")
                # Exceptions have no parent node: bind them to the scoped API endpoint.
                for item in evidence:
                    path = urlparse(item.canonical_url)
                    if (path.hostname != "api.gleif.org"
                            or path.path != f"/api/v1/lei-records/{subject.lei}/{direction}-reporting-exception"):
                        raise ValueError("Reporting exception endpoint belongs to another subject.")
                if attributes.get("lei", subject.lei) != subject.lei:
                    raise ValueError("Reporting exception subject mismatch.")
                output.append(self._record(dataset, record, "reporting_exception", "confirmed",
                                           {"direction": direction, "exception_reasons": reasons,
                                            "reported_attributes": attributes}))
            elif kind == "relationship-records":
                relationship = attributes["relationship"]
                start, end = relationship["startNode"]["id"], relationship["endNode"]["id"]
                if not isinstance(start, str) or not isinstance(end, str) or not start or not end or start == end:
                    raise ValueError("Invalid relationship endpoints.")
                expected_type = ("IS_ULTIMATELY_CONSOLIDATED_BY" if direction == "ultimate-parent"
                                 else "IS_DIRECTLY_CONSOLIDATED_BY")
                if (relationship["type"] != expected_type
                        or (end if direction == "direct-children" else start) != subject.lei
                        or not isinstance(relationship["status"], str) or not relationship["status"]):
                    raise ValueError("Relationship direction, type or status mismatch.")
                output.append(self._record(dataset, record, "consolidation_relationship", "confirmed",
                                           {"direction": direction, "relationship": relationship,
                                            "registration": attributes.get("registration", {}),
                                            "valid_from": attributes.get("validFrom"),
                                            "valid_to": attributes.get("validTo")}))
            else:
                raise ValueError("Unsupported relationship record type.")
        dataset.coverage.records_checked = len(dataset.records)
        return output

    def _norway_identity(self, dataset, subject, number):
        if len(dataset.records) != 1:
            raise ValueError("Norwegian organization lookup did not return one identity.")
        record = dataset.records[0]
        entity = EntityRecord.model_validate({key: value for key, value in record.items()
                                            if key != "observation_ids"})
        self._evidence(dataset, record)
        if (entity.source_id != NORWAY or entity.registration_id != number
                or entity.source_record_id != number or entity.jurisdiction != "NO"):
            raise ValueError("Norway organization identity mismatch.")
        party = PartyInput(legal_name=subject.legal_name, aliases=subject.aliases,
                           registration_id=subject.registration_id, registration_authority=subject.registration_authority,
                           jurisdiction=subject.jurisdiction, lei=subject.lei)
        candidate = IdentityCandidate(candidate_id="norway_link", source_id=NORWAY, source_record_id=number,
                                      legal_name=entity.legal_name, registration_id=number,
                                      registration_authority=NORWAY, jurisdiction="NO")
        match = EntityResolver().match(party, candidate)
        if match.status in {"conflict", "no_match"} or "exact_name_or_alias" not in match.reason_codes:
            raise ValueError("Norway legal name or registry scope conflicts with confirmed party.")
        dataset.coverage.records_checked = 1
        return "confirmed" if match.status == "confirmed" else "pending", record["observation_ids"]

    def _roles(self, dataset, lookup, number, attribution, lookup_ids):
        output = []
        seen = set()
        for record in dataset.records:
            role = OrganizationRole.model_validate({key: value for key, value in record.items()
                                                   if key != "observation_ids"})
            if (role.source_id != NORWAY or role.organization_number != number
                    or not role.display_name.strip() or role.source_record_id in seen):
                raise ValueError("Role belongs to another organization or is duplicated.")
            seen.add(role.source_record_id)
            evidence = self._evidence(dataset, record)
            if any(urlparse(item.canonical_url).path != f"/enhetsregisteret/api/enheter/{number}/roller"
                   or urlparse(item.canonical_url).hostname != "data.brreg.no" for item in evidence):
                raise ValueError("Roles endpoint belongs to another organization.")
            evidence = [*evidence, *(lookup.evidence[key] for key in lookup_ids)]
            output.append(self._record(dataset, record, "organizational_role", attribution,
                                       {**role.model_dump(mode="json"),
                                        "identity_lookup_run_id": lookup.coverage.source_run_id}, evidence=evidence))
        dataset.coverage.records_checked = len(dataset.records)
        return output

    @staticmethod
    def _finding(record, subject):
        details = record.details
        if record.kind == "consolidation_relationship":
            rel = details["relationship"]
            claim = f"GLEIF reports {rel['startNode']['id']} {rel['type']} {rel['endNode']['id']}; status {rel['status']}."
        elif record.kind == "reporting_exception":
            claim = f"GLEIF {details['direction']} reporting exception: {', '.join(details['exception_reasons'])}."
        else:
            status = "deregistered" if details["deregistered"] else "registered"
            claim = (f"Norway registry reports {details['display_name']} as {details['role_name']} "
                     f"({status}); organization identity linkage {record.attribution}.")
        evidence = record.evidence[0]
        return Finding(
            finding_id=stable_id("finding", record.record_id), branch_id="ownership",
            claim_type=record.kind, claim=claim[:2000], subject=subject.legal_name,
            subject_id=subject.candidate_id if record.attribution == "confirmed" else None,
            claim_key=f"ownership.{record.kind}", claim_value=record.source_record_id,
            claim_cardinality="multiple", source_id=record.source_id, source_name=record.source_id,
            source_record_id=record.source_record_id, source_run_id=record.source_run_id,
            source_url=evidence.canonical_url, observation_ids=[item.observation_id for item in record.evidence],
            content_hash=evidence.content_hash, connector_version=evidence.connector_version,
            observed_at=evidence.observed_at, evidence_mode="live_source",
            verification_status=f"source_reported_identity_{record.attribution}")
