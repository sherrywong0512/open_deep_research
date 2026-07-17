"""Convert research-tool source output into grounded diligence evidence packages."""

import json
import re
from datetime import date
from typing import Any

from open_deep_research.diligence_evidence import (
    build_evidence_package,
    validate_source_url,
)

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
    sources_by_url: dict[str, list[dict[str, str]]] = {}
    for source in research_sources:
        sources_by_url.setdefault(source["source_url"], []).append(source)
    raw_mappings = json.loads(mappings_json)
    if not isinstance(raw_mappings, list):
        raise ValueError("mappings_json must contain a JSON array")

    candidates: list[dict[str, Any]] = []
    rejected_mappings: list[dict[str, Any]] = []
    for raw_mapping in raw_mappings:
        mapping = raw_mapping if isinstance(raw_mapping, dict) else {}
        source_url = mapping.get("source_url")
        if not isinstance(source_url, str):
            rejected_mappings.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "missing_fields": [],
                    "reason": "source_not_observed",
                }
            )
            continue

        source_observations = sources_by_url.get(source_url)
        if source_observations is None:
            rejected_mappings.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "missing_fields": [],
                    "reason": "source_not_observed",
                }
            )
            continue

        key_excerpt = mapping.get("key_excerpt")
        if not isinstance(key_excerpt, str) or not any(
            _normalise_text(key_excerpt)
            in _normalise_text(source["research_excerpt"])
            for source in source_observations
        ):
            rejected_mappings.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "missing_fields": [],
                    "reason": "excerpt_not_observed",
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
    sources: list[dict[str, str]] = []
    for match in _SOURCE_PATTERN.finditer(research_output):
        source_url = match.group("url").strip()
        try:
            validate_source_url(source_url)
        except ValueError:
            continue
        sources.append(
            {
                "title": match.group("title").strip(),
                "source_url": source_url,
                "research_excerpt": match.group("summary").strip(),
                "accessed_at": accessed_at,
                "limitations": "Research output is a source observation, not verified evidence.",
            }
        )
    return sources


def _validate_access_date(accessed_at: str) -> None:
    """Require the same complete ISO date format used by evidence candidates."""
    if not _ISO_DATE_PATTERN.fullmatch(accessed_at):
        raise ValueError("accessed_at must use the YYYY-MM-DD ISO date format")
    date.fromisoformat(accessed_at)


def _normalise_text(text: str) -> str:
    """Fold case and whitespace before comparing an excerpt to its source observation."""
    return " ".join(text.casefold().split())
