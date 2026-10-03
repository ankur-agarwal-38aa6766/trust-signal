"""Official World Bank debarment data, with source eligibility flags preserved."""

import re

from trust_signal.connectors.base import SourceBatch, SourceEvent
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError


class WorldBankDebarmentAdapter(HttpSource):
    source_id = "worldbank_debarment"
    page_url = "https://www.worldbank.org/en/Projects-operations/procurement/debarred-firms"
    data_url = "https://apigwext.worldbank.org/dvsvc/v1.0/json/APPLICATION/ADOBE_EXPRNCE_MGR/FIRM/SANCTIONED_FIRM"

    def fetch_snapshot(self) -> SourceBatch:
        page = self.get(self.page_url)
        # The official page publishes this browser-access key, not a private project credential.
        match = re.search(r'var\s+propApiKey\s*=\s*"([^"\r\n]+)"', page.text)
        if match is None:
            raise SourceSchemaError("World Bank public data access discovery changed.")
        response = self.get(self.data_url, headers={"apikey": match[1]})
        try:
            payload = response.json()
            rows = payload["response"]["ZPROCSUPP"]
            if not isinstance(rows, list) or not rows:
                raise ValueError("No sanctioned supplier records")
            records = []
            seen = set()
            for row in rows:
                identifier = str(row["SUPP_ID"])
                name = row["SUPP_NAME"]
                if identifier in seen or not isinstance(name, str) or not name.strip():
                    raise ValueError("Invalid or duplicate supplier identity")
                seen.add(identifier)
                records.append(SourceEvent(source_id=self.source_id, source_record_id=identifier,
                    title=name.strip(), subject_name=name.strip(), canonical_url=self.page_url,
                    event_type="procurement_eligibility", procedural_status="debarment_listing",
                    jurisdiction=row.get("LAND1"), outcome=row.get("ELIG_STAT"),
                    source_category=row.get("DEBAR_TYPE"),
                    metadata={key: row.get(key) for key in (
                        "SUPP_TYPE_CODE", "INELIG_FLG", "SUPP_ELIG_STAT", "DEBAR_TYPE", "ELIG_STAT",
                        "DEBAR_FROM_DATE", "DEBAR_TO_DATE", "DEBAR_REASON", "INELIGIBLY_STATUS", "LAST_REFRESH_DATE",
                    )}).model_dump(mode="json"))
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceSchemaError("World Bank debarment JSON failed validation.") from exc
        return SourceBatch(observations=[
            self.observation(page, "public-access-page", {"data_endpoint": self.data_url}, "text/html"),
            self.observation(response, "sanctioned-suppliers", payload, "application/json"),
        ], records=records, limitations=[
            "Source eligibility flags and dates are retained; this is not a criminal conviction.",
            "Other sanctions and cross-debarment must be interpreted from source flags, not inferred from a name.",
        ])
