"""Presentation states derived from actual identity command results."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Indicator:
    label: str
    tone: str
    symbol: str


def search_indicator(mode, result=None, *, pending=False, error=False) -> Indicator:
    if str(mode) != "gleif_live":
        return Indicator("Fixture mode · live GLEIF off", "muted", "science")
    if pending:
        return Indicator("GLEIF Auto-Suggest Searching…", "blue", "progress_activity")
    if error or (result and (result.error or result.coverage in {"failed", "blocked"})):
        label = "Rate Limited" if result and result.http_status == 429 else "Unavailable"
        return Indicator(f"GLEIF Auto-Suggest {label}", "red", "error")
    if result and result.coverage == "partial":
        return Indicator("GLEIF Auto-Suggest Partial", "orange", "warning")
    if result:
        return Indicator("GLEIF Real-time Auto-Suggest Active", "green", "query_stats")
    return Indicator("GLEIF Auto-Suggest Ready", "muted", "query_stats")


def verification_indicator(result, mode) -> Indicator:
    if result is None:
        return Indicator("Not verified", "muted", "radio_button_unchecked")
    if str(mode) != "gleif_live" or result.status == "demo":
        return Indicator("Demo selection", "muted", "science")
    if result.status == "verified":
        return Indicator("Verified", "green", "check_circle")
    label = "Identity conflict" if result.status == "conflict" else "Not verified"
    return Indicator(label, "red", "error")
