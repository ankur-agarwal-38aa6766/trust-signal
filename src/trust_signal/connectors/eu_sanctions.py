"""European Commission financial-sanctions XML 1.1 public distribution."""

from xml.etree import ElementTree as ET

from trust_signal.connectors.base import SanctionsListing, SanctionsSnapshot
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError


class EUSanctionsAdapter(HttpSource):
    source_id = "eu_financial_sanctions"
    # This public distribution URL is published in the EU data portal's dataset metadata.
    url = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"

    def fetch_snapshot(self) -> SanctionsSnapshot:
        response = self.get(self.url)
        try:
            root = ET.fromstring(response.content)
            if root.tag.split("}")[-1] != "export":
                raise ValueError("Wrong root")
            listings = []
            for node in root.findall("{*}sanctionEntity"):
                names = [n.attrib["wholeName"] for n in node.findall("{*}nameAlias") if n.attrib.get("wholeName")]
                subject = node.find("{*}subjectType")
                kind = subject.attrib["code"] if subject is not None else None
                identifier = node.attrib.get("euReferenceNumber") or node.attrib.get("logicalId")
                if not names or not identifier or kind not in {"person", "enterprise"}:
                    raise ValueError("Invalid financial sanctions identity")
                regulation = node.find("{*}regulation")
                regime = regulation.attrib.get("programme") if regulation is not None else None
                listings.append(SanctionsListing(source_id=self.source_id, source_record_id=identifier,
                    legal_name=names[0], aliases=list(dict.fromkeys(names[1:])),
                    list_type="individual" if kind == "person" else "entity", sanctions_regime=regime,
                    listed_on=regulation.attrib.get("publicationDate") if regulation is not None else None,
                    measures=["Financial sanctions designation"],
                    comments=node.findtext("{*}remark")))
            if not listings or len({n.source_record_id for n in listings}) != len(listings):
                raise ValueError("Empty or duplicate EU records")
        except (ET.ParseError, ValueError, TypeError, KeyError) as exc:
            raise SourceSchemaError("EU financial sanctions XML failed validation.") from exc
        return SanctionsSnapshot(observation=self.observation(response, "eu-financial-sanctions.xml",
            {"generated_on": root.attrib.get("generationDate"), "record_count": len(listings)}), listings=listings)
