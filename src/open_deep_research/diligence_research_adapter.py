"""Convert research-tool source output into grounded diligence evidence packages."""

import json
import re
from datetime import date
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from open_deep_research.diligence_evidence import build_evidence_package

_SOURCE_PATTERN = re.compile(
    r"--- SOURCE \d+: (?P<title>[^\n]+) ---\s*\n"
    r"URL: (?P<url>https?://[^\s]+)\s*\n\s*SUMMARY:\s*\n"
    r"(?P<summary>.*?)(?=\n\s*-{20,}\s*(?:\n|$)|\Z)",
    re.DOTALL,
)
_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def build_evidence_package_from_research_output(
    request_json: str,
    research_output: str,
    mappings_json: str,
    accessed_at: str,
) -> str:
    """Build evidence only from mappings grounded in the supplied research sources."""
    _validate_access_date(accessed_at)
    research_sources = extract_research_sources(research_output, accessed_at)
    observed_urls = {_normalise_url(item["source_url"]) for item in research_sources}
    raw_mappings = json.loads(mappings_json)
    if not isinstance(raw_mappings, list):
        raise ValueError("mappings_json must contain a JSON array")

    candidates: list[dict[str, Any]] = []
    rejected_mappings: list[dict[str, Any]] = []
    for raw_mapping in raw_mappings:
        mapping = raw_mapping if isinstance(raw_mapping, dict) else {}
        source_url = mapping.get("source_url")
        if not isinstance(source_url, str) or _normalise_url(source_url) not in observed_urls:
            rejected_mappings.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "missing_fields": [],
                    "reason": "source_not_observed",
                }
            )
            continue

        candidate = {**mapping, "accessed_at": accessed_at}
        candidates.append(candidate)

    package = json.loads(
        build_evidence_package(
            request_json,
            json.dumps(candidates, ensure_ascii=False),
        )
    )
    package["rejected_evidence"].extend(rejected_mappings)
    package["research_sources"] = research_sources
    return json.dumps(package, ensure_ascii=False)


def extract_research_sources(research_output: str, accessed_at: str) -> list[dict[str, str]]:
    """Extract source observations from the built-in Tavily search-output format."""
    _validate_access_date(accessed_at)
    return [
        {
            "title": match.group("title").strip(),
            "source_url": match.group("url").strip(),
            "research_excerpt": match.group("summary").strip(),
            "accessed_at": accessed_at,
            "limitations": "Research output is a source observation, not verified evidence.",
        }
        for match in _SOURCE_PATTERN.finditer(research_output)
    ]


def _validate_access_date(accessed_at: str) -> None:
    """Require the same complete ISO date format used by evidence candidates."""
    if not _ISO_DATE_PATTERN.fullmatch(accessed_at):
        raise ValueError("accessed_at must use the YYYY-MM-DD ISO date format")
    date.fromisoformat(accessed_at)


def _normalise_url(url: str) -> str:
    """Normalise HTTP URLs so equivalent trailing slashes compare consistently."""
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))
