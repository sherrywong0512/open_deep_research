"""Convert research-tool source output into grounded diligence evidence packages."""

import gzip
import json
import re
import socket
import ssl
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from http.client import HTTPResponse
from ipaddress import ip_address
from typing import Any, Callable, Literal
from urllib.parse import urlsplit

from open_deep_research.diligence_evidence import (
    DiligenceRequest,
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
_MAX_SOURCE_BYTES = 2_000_000


class _VisibleTextExtractor(HTMLParser):
    """Extract display text without treating scripts or styles as evidence."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._suppressed_tags: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._suppressed_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._suppressed_tags and self._suppressed_tags[-1] == tag:
            self._suppressed_tags.pop()

    def handle_data(self, data: str) -> None:
        if not self._suppressed_tags:
            self.parts.append(data)


@dataclass(frozen=True)
class SourceVerification:
    """Describe whether a mapped excerpt was found in fetched public content."""

    status: Literal["verified", "not_checked", "excerpt_not_found", "fetch_failed"]
    content_sha256: str | None = None
    fetched_at: str | None = None


SourceVerifier = Callable[[str, str], SourceVerification]


def build_evidence_package_from_research_output(
    request_json: str,
    research_output: str,
    mappings_json: str,
    accessed_at: str,
    source_verifier: SourceVerifier | None = None,
) -> str:
    """Build evidence only from mappings grounded in the supplied research sources."""
    _validate_access_date(accessed_at)
    research_sources = extract_research_sources(research_output, accessed_at)
    return _build_evidence_package_from_sources(
        request_json, research_sources, mappings_json, accessed_at, source_verifier
    )


def build_evidence_package_from_research_record(
    request_json: str,
    research_record_json: str,
    mappings_json: str,
    accessed_at: str,
    source_verifier: SourceVerifier | None = None,
) -> str:
    """Build evidence from a platform-neutral external-agent research record."""
    _validate_access_date(accessed_at)
    research_sources = extract_research_record_sources(research_record_json, accessed_at)
    return _build_evidence_package_from_sources(
        request_json, research_sources, mappings_json, accessed_at, source_verifier
    )


def _build_evidence_package_from_sources(
    request_json: str,
    research_sources: list[dict[str, str]],
    mappings_json: str,
    accessed_at: str,
    source_verifier: SourceVerifier | None,
) -> str:
    """Apply the same source-to-mapping gate regardless of the research provider."""
    sources_by_url: dict[str, list[dict[str, str]]] = {}
    for source in research_sources:
        sources_by_url.setdefault(source["source_url"], []).append(source)
    request = DiligenceRequest.model_validate_json(request_json)
    claim_priorities = {claim.id: claim.priority for claim in request.claims}
    raw_mappings = json.loads(mappings_json)
    if not isinstance(raw_mappings, list):
        raise ValueError("mappings_json must contain a JSON array")

    candidates: list[dict[str, Any]] = []
    rejected_mappings: list[dict[str, Any]] = []
    source_verifications: list[dict[str, str | None]] = []
    for raw_mapping in raw_mappings:
        mapping = raw_mapping if isinstance(raw_mapping, dict) else {}
        claim_id = mapping.get("claim_id")
        claim_priority = (
            claim_priorities.get(claim_id) if isinstance(claim_id, str) else None
        )
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

        if (
            claim_priority == "high"
            and _normalise_text(str(mapping.get("fact", "")))
            != _normalise_text(key_excerpt)
        ):
            rejected_mappings.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "missing_fields": [],
                    "reason": "fact_not_direct_quote",
                }
            )
            continue

        verification = (
            source_verifier(source_url, key_excerpt)
            if source_verifier is not None
            else SourceVerification(status="not_checked")
        )
        source_verifications.append(
            {
                "source_url": source_url,
                "key_excerpt": key_excerpt,
                **asdict(verification),
            }
        )
        if verification.status != "verified":
            rejected_mappings.append(
                {
                    "claim_id": mapping.get("claim_id"),
                    "missing_fields": [],
                    "reason": "source_not_verified",
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
    package["source_verifications"] = source_verifications
    return json.dumps(package, ensure_ascii=False)


def fetch_public_source(source_url: str, key_excerpt: str) -> SourceVerification:
    """Fetch a public URL and verify that its response contains the mapped excerpt."""
    try:
        hostname, port, address = _public_network_target(source_url)
    except (OSError, ValueError):
        return SourceVerification(status="fetch_failed")
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        content, content_encoding, content_type = _fetch_pinned_public_content(
            source_url, hostname, port, address
        )
    except (OSError, ValueError):
        return SourceVerification(status="fetch_failed", fetched_at=fetched_at)

    if len(content) > _MAX_SOURCE_BYTES:
        return SourceVerification(status="fetch_failed", fetched_at=fetched_at)
    content_sha256 = sha256(content).hexdigest()
    try:
        page_text = _extract_public_text(content, content_encoding, content_type)
    except (OSError, ValueError):
        return SourceVerification(
            status="fetch_failed",
            content_sha256=content_sha256,
            fetched_at=fetched_at,
        )
    if _normalise_text(key_excerpt) not in _normalise_text(page_text):
        return SourceVerification(
            status="excerpt_not_found",
            content_sha256=content_sha256,
            fetched_at=fetched_at,
        )
    return SourceVerification(
        status="verified", content_sha256=content_sha256, fetched_at=fetched_at
    )


def _public_network_target(source_url: str) -> tuple[str, int, str]:
    """Return one verified public IP to pin for a source request."""
    validate_source_url(source_url)
    parsed = urlsplit(source_url)
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("source URL must include a hostname")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = {ip_address(hostname)}
    except ValueError:
        addresses = {
            ip_address(result[4][0])
            for result in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        }
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("source URL must resolve only to public IP addresses")
    return hostname, port, str(sorted(addresses, key=str)[0])


def _fetch_pinned_public_content(
    source_url: str, hostname: str, port: int, address: str
) -> tuple[bytes, str | None, str | None]:
    """Fetch one response through a socket pinned to a previously verified IP."""
    parsed = urlsplit(source_url)
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    host_header = hostname if parsed.port is None else f"{hostname}:{port}"
    request_bytes = (
        f"GET {target} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        "User-Agent: open-deep-research-diligence/1.0\r\n"
        "Accept: text/plain, text/html, application/xhtml+xml\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")

    with socket.create_connection((address, port), timeout=10) as raw_socket:
        socket_for_response = raw_socket
        if parsed.scheme == "https":
            context = ssl.create_default_context()
            socket_for_response = context.wrap_socket(raw_socket, server_hostname=hostname)
        try:
            socket_for_response.sendall(request_bytes)
            response = HTTPResponse(socket_for_response)
            response.begin()
            if response.status < 200 or response.status >= 300:
                raise ValueError("source response must be a non-redirect success")
            return (
                response.read(_MAX_SOURCE_BYTES + 1),
                response.getheader("Content-Encoding"),
                response.getheader("Content-Type"),
            )
        finally:
            if socket_for_response is not raw_socket:
                socket_for_response.close()


def _extract_public_text(
    content: bytes, content_encoding: str | None, content_type: str | None
) -> str:
    """Decode supported static text/HTML responses for direct-quote matching."""
    encoding = (content_encoding or "").casefold().strip()
    if encoding in {"", "identity"}:
        decoded = content
    elif encoding == "gzip":
        decoded = gzip.decompress(content)
    else:
        raise ValueError("unsupported content encoding")
    if len(decoded) > _MAX_SOURCE_BYTES:
        raise ValueError("decoded source exceeds maximum size")

    text = decoded.decode("utf-8", errors="replace")
    if "html" not in (content_type or "").casefold():
        return text
    parser = _VisibleTextExtractor()
    parser.feed(text)
    parser.close()
    return " ".join(parser.parts)


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


def extract_research_record_sources(
    research_record_json: str, accessed_at: str
) -> list[dict[str, str]]:
    """Extract safe source observations from a Codex or other-agent JSON record.

    The record is intentionally small and provider-neutral: ``sources`` must be a
    JSON array whose entries contain ``title``, ``source_url``, and
    ``research_excerpt``. The caller supplies the access date so a provider cannot
    silently claim a different retrieval date.
    """
    _validate_access_date(accessed_at)
    raw_record = json.loads(research_record_json)
    if not isinstance(raw_record, dict):
        raise ValueError("research_record_json must contain a JSON object")
    raw_sources = raw_record.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("research_record_json must contain a sources JSON array")

    sources: list[dict[str, str]] = []
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            continue
        title = raw_source.get("title")
        source_url = raw_source.get("source_url")
        research_excerpt = raw_source.get("research_excerpt")
        if (
            not isinstance(title, str)
            or not isinstance(source_url, str)
            or not isinstance(research_excerpt, str)
            or not title.strip()
            or not source_url.strip()
            or not research_excerpt.strip()
        ):
            continue
        try:
            validate_source_url(source_url)
        except ValueError:
            continue
        sources.append(
            {
                "title": title.strip(),
                "source_url": source_url.strip(),
                "research_excerpt": research_excerpt.strip(),
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
