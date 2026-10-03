"""FCDO UK Sanctions List; not the withdrawn OFSI consolidated export."""

from xml.etree import ElementTree as ET

from trust_signal.connectors.base import SanctionsListing, SanctionsSnapshot
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError, xml_text


class UKSanctionsAdapter(HttpSource):
    source_id = "uk_fcdo_sanctions"
    url = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"

    def fetch_snapshot(self) -> SanctionsSnapshot:
        response = self.get(self.url)
        try:
            root = ET.fromstring(response.content)
            if root.tag != "Designations":
                raise ValueError("Wrong root")
            listings = []
            for node in root.findall("Designation"):
                names = [(" ".join(filter(None, [xml_text(n, f"Name{i}") for i in range(1, 7)])),
                          xml_text(n, "NameType")) for n in node.findall("Names/Name")]
                primary = next((name for name, kind in names if name and kind and kind.casefold() == "primary name"), None)
                identifier = xml_text(node, "UniqueID")
                kind = xml_text(node, "IndividualEntityShip")
                if not identifier or not primary or kind not in {"Individual", "Entity", "Ship"}:
                    raise ValueError("Invalid designation identity")
                measures = [flag.tag for flag in node.findall("SanctionsImposedIndicators/*")
                            if (flag.text or "").strip().lower() == "true"]
                listings.append(SanctionsListing(source_id=self.source_id, source_record_id=identifier,
                    legal_name=primary, list_type="vessel" if kind == "Ship" else kind.lower(),
                    listed_on=xml_text(node, "DateDesignated"), sanctions_regime=xml_text(node, "RegimeName"),
                    aliases=[name for name, _ in names if name and name != primary] +
                            [n.text.strip() for n in node.findall("NonLatinNames/NonLatinName/NameNonLatinScript")
                             if n.text and n.text.strip()], measures=measures,
                    jurisdiction=xml_text(node, "Addresses/Address/AddressCountry"),
                    comments=xml_text(node, "UKStatementofReasons") or xml_text(node, "OtherInformation")))
            if not listings or len({n.source_record_id for n in listings}) != len(listings):
                raise ValueError("Empty or duplicate designations")
        except (ET.ParseError, ValueError, TypeError) as exc:
            raise SourceSchemaError("UK Sanctions List XML failed validation.") from exc
        return SanctionsSnapshot(observation=self.observation(response, "uk-sanctions.xml",
            {"generated_on": xml_text(root, "DateGenerated"), "record_count": len(listings)}), listings=listings)
