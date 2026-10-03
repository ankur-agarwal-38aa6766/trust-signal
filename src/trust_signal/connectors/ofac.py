"""OFAC's official SDN list; non-SDN lists are a separate coverage scope."""

from xml.etree import ElementTree as ET

from trust_signal.connectors.base import SanctionsListing, SanctionsSnapshot
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError, xml_text


class OFACAdapter(HttpSource):
    source_id = "us_ofac_sdn"
    url = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"

    def fetch_snapshot(self) -> SanctionsSnapshot:
        response = self.get(self.url)
        try:
            root = ET.fromstring(response.content)
            if root.tag.split("}")[-1] != "sdnList":
                raise ValueError("Wrong root")
            listings = []
            for node in root.findall("{*}sdnEntry"):
                identifier = xml_text(node, "{*}uid")
                name = " ".join(filter(None, [xml_text(node, "{*}firstName"), xml_text(node, "{*}lastName")]))
                kind = xml_text(node, "{*}sdnType")
                if not identifier or not name or kind not in {"Individual", "Entity", "Vessel", "Aircraft"}:
                    raise ValueError("Invalid SDN identity")
                programs = [n.text.strip() for n in node.findall("{*}programList/{*}program") if n.text]
                aliases = [" ".join(filter(None, [xml_text(a, "{*}firstName"), xml_text(a, "{*}lastName")]))
                           for a in node.findall("{*}akaList/{*}aka")]
                listings.append(SanctionsListing(source_id=self.source_id, source_record_id=identifier,
                    legal_name=name, list_type=kind.lower(), programs=programs,
                    sanctions_regime="; ".join(programs) or None, aliases=[a for a in aliases if a],
                    jurisdiction=xml_text(node, "{*}addressList/{*}address/{*}country"),
                    comments=xml_text(node, "{*}remarks"), measures=["SDN designation"]))
            if not listings or len({n.source_record_id for n in listings}) != len(listings):
                raise ValueError("Empty or duplicate SDN records")
        except (ET.ParseError, ValueError, TypeError) as exc:
            raise SourceSchemaError("OFAC SDN XML failed validation.") from exc
        observation = self.observation(response, "sdn.xml", {"root_tag": root.tag,
            "record_count": len(listings), "published_on": xml_text(root, "{*}publshInformation/{*}Publish_Date")},
            canonical_url=self.url)
        return SanctionsSnapshot(observation=observation, listings=listings)
