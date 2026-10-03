"""Worldwide GDELT DOC discovery of article metadata, not licensed full text."""

import hashlib
from urllib.parse import urlparse

from trust_signal.connectors.base import SourceBatch, SourceEvent
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError


class GDELTNewsAdapter(HttpSource):
    source_id = "gdelt_doc_news"
    url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def search(self, name: str) -> SourceBatch:
        name = name.strip()
        if len(name) < 2 or len(name) > 200 or any(char in name for char in '"\\\n\r():'):
            raise ValueError("Company name contains unsupported search syntax")
        response = self.get(self.url, {"query": f'"{name}"', "mode": "artlist", "format": "json",
            "maxrecords": 50, "timespan": "24h", "sort": "datedesc"})
        try:
            payload = response.json()
            articles = payload["articles"]
            if not isinstance(articles, list):
                raise TypeError("Article array required")
            records = []
            seen = set()
            for article in articles:
                url = article["url"]
                title = article["title"]
                if urlparse(url).scheme not in {"http", "https"} or not urlparse(url).hostname or not isinstance(title, str) or not title.strip():
                    raise ValueError("Invalid article metadata")
                if url in seen:
                    continue
                seen.add(url)
                records.append(SourceEvent(source_id=self.source_id,
                    source_record_id=hashlib.sha256(url.encode()).hexdigest(), title=title,
                    canonical_url=url, event_type="news_report",
                    metadata={"provider_seen_at": article.get("seendate"),
                              "publisher_domain": article.get("domain"), "language": article.get("language"),
                              "source_country": article.get("sourcecountry"), "publisher_trust": "not_assessed",
                              "content_rights": "metadata_and_links_only"}).model_dump(mode="json"))
        except (KeyError, ValueError, TypeError) as exc:
            raise SourceSchemaError("GDELT metadata JSON failed validation.") from exc
        return SourceBatch(observations=[self.observation(response, "article-discovery", payload, "application/json")],
            records=records, complete=False, limitations=[
                "Bounded last-24-hour discovery (50 results), not complete worldwide coverage.",
                "Search results are unmatched candidates; publisher trust is not inherited from GDELT.",
                "Seen time is not publication time. Publisher full-text rights are not granted by this connector.",
            ])
