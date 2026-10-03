"""Official RSS/Atom metadata discovery; never infer guilt from a headline."""

from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from trust_signal.connectors.base import SourceBatch, SourceEvent
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError, xml_text

ATOM = "{http://www.w3.org/2005/Atom}"
FACET = "{https://www.thegazette.co.uk/facets}"


def parse_feed(response, source_id: str, event_type: str, host: str) -> tuple[list[dict], bool]:
    try:
        root = ET.fromstring(response.content)
        atom = root.tag == ATOM + "feed"
        if not atom and root.tag != "rss":
            raise ValueError("Unsupported feed root")
        entries = root.findall(ATOM + "entry") if atom else root.findall("channel/item")
        records = []
        seen = set()
        for entry in entries:
            title = xml_text(entry, ATOM + "title" if atom else "title")
            if atom:
                link = next((n.attrib.get("href") for n in entry.findall(ATOM + "link")
                             if n.attrib.get("rel", "alternate") == "alternate"
                             and n.attrib.get("type", "text/html") in {"text/html", "application/xhtml+xml"}), None)
                identifier = xml_text(entry, ATOM + "id")
            else:
                link = xml_text(entry, "link")
                identifier = xml_text(entry, "guid") or link
            if not title or not identifier or not link or urlparse(link).scheme != "https" or urlparse(link).hostname != host:
                raise ValueError("Invalid official feed identity or link")
            if identifier in seen:
                raise ValueError("Duplicate feed entry")
            seen.add(identifier)
            record = SourceEvent(source_id=source_id, source_record_id=identifier,
                title=title, canonical_url=link, event_type=event_type,
                jurisdiction="GB",
                published_at=xml_text(entry, ATOM + "published" if atom else "pubDate"),
                updated_at=xml_text(entry, ATOM + "updated") if atom else None,
                source_category=xml_text(entry, "category") if not atom else None)
            if event_type == "court_record":
                record.procedural_status = "judgment_published"
                record.metadata = {"document_uri": xml_text(entry, "{https://caselaw.nationalarchives.gov.uk}uri")}
            if event_type == "insolvency_notice":
                code = xml_text(entry, FACET + "notice-code")
                if not code or not code.startswith("24"):
                    raise ValueError("Non-corporate notice returned by corporate feed")
                record.source_category = code
                record.metadata = {"notice_publication_status": xml_text(entry, FACET + "status")}
                # Official notice codes distinguish petitions from court orders and dismissals.
                record.procedural_status = "proceeding" if code == "2450" else "unknown"
                if code == "2452":
                    record.procedural_status = "decision"
                    record.outcome = "winding_up_order_published"
                elif code == "2461":
                    record.procedural_status = "decision"
                    record.outcome = "petition_dismissal_published"
            records.append(record.model_dump(mode="json"))
        has_next = atom and any(n.attrib.get("rel") == "next" for n in root.findall(ATOM + "link"))
        return records, has_next
    except (ET.ParseError, ValueError, TypeError, KeyError) as exc:
        raise SourceSchemaError("Official feed metadata failed validation.") from exc


class FCANewsAdapter(HttpSource):
    source_id = "uk_fca_newsroom"
    url = "https://www.fca.org.uk/news/rss.xml"

    def fetch_recent(self) -> SourceBatch:
        response = self.get(self.url)
        records, _ = parse_feed(response, self.source_id, "regulator_announcement", "www.fca.org.uk")
        return SourceBatch(observations=[self.observation(response, "recent-news", {"record_count": len(records)})],
            records=records, complete=False, limitations=[
                "Recent official newsroom feed, not comprehensive enforcement history.",
                "Announcements are unclassified metadata; review the primary notice before allegation, proceeding or final-decision classification.",
            ])


class GazetteInsolvencyAdapter(HttpSource):
    source_id = "uk_gazette_insolvency"
    url = "https://www.thegazette.co.uk/insolvency/notice/data.feed"

    def search(self, name: str, max_pages: int = 1):
        if not name.strip() or len(name) > 200 or not 1 <= max_pages <= 100:
            raise ValueError("A bounded party name and page limit are required")
        for page in range(1, max_pages + 1):
            response = self.get(self.url, {"categorycode": "24", "text": name.strip(),
                "results-page-size": 20, "results-page": page})
            records, has_next = parse_feed(response, self.source_id, "insolvency_notice", "www.thegazette.co.uk")
            yield SourceBatch(observations=[self.observation(response, f"corporate-notices:{page}", {"record_count": len(records)})],
                records=records, complete=not has_next or page < max_pages,
                limitations=["UK corporate notices only; source search results require identity confirmation.",
                             "Petition, order and dismissal labels are distinct; order finality remains unknown."])
            if not has_next:
                break


class FindCaseLawAdapter(HttpSource):
    source_id = "uk_find_case_law"
    url = "https://caselaw.nationalarchives.gov.uk/atom.xml"

    def search(self, name: str, max_pages: int = 1):
        if not name.strip() or len(name) > 200 or not 1 <= max_pages <= 100:
            raise ValueError("A bounded party name and page limit are required")
        for page in range(1, max_pages + 1):
            response = self.get(self.url, {"party": name.strip(), "per_page": 20,
                                         "minimum_availability": "metadata", "page": page})
            records, has_next = parse_feed(response, self.source_id, "court_record", "caselaw.nationalarchives.gov.uk")
            yield SourceBatch(observations=[self.observation(response, f"party-search:{page}", {"record_count": len(records)})],
                records=records, complete=not has_next or page < max_pages,
                limitations=["UK published judgments metadata only; no judgment body analysis.",
                             "Publication is not an adverse outcome, conviction or proof of finality.",
                             "Automated use requires the project licensing gate to be satisfied."])
            if not has_next:
                break
