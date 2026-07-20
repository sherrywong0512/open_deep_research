"""Behavioral tests for converting research-tool output into evidence packages."""

import json
import socket

import pytest

from open_deep_research.diligence_research_adapter import (
    SourceVerification,
    build_evidence_package_from_research_output,
    build_evidence_package_from_research_record,
    extract_research_sources,
    fetch_public_source,
)


def _request_json() -> str:
    return json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [
                {
                    "id": "license",
                    "statement": "公司持有某项许可",
                    "priority": "high",
                }
            ],
        }
    )


def _research_output() -> str:
    return """Search results:

--- SOURCE 1: License registry ---
URL: https://regulator.example/licenses/ABC-123

SUMMARY:
Registry lists license ABC-123 for Example Company.

--------------------------------------------------------------------------------
"""


def _verified_source(_source_url: str, _key_excerpt: str) -> SourceVerification:
    return SourceVerification(status="verified", content_sha256="a" * 64)


def test_builds_evidence_only_when_mapping_points_to_observed_source() -> None:
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "license ABC-123 for Example Company",
                "key_excerpt": "license ABC-123 for Example Company",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_output(
            _request_json(),
            _research_output(),
            mappings_json,
            "2026-07-17",
            source_verifier=_verified_source,
        )
    )

    assert package["usable_evidence"][0]["accessed_at"] == "2026-07-17"
    assert package["coverage"][0]["status"] == "covered"
    assert package["research_sources"][0]["source_url"] == (
        "https://regulator.example/licenses/ABC-123"
    )


def test_rejects_mapping_that_does_not_exactly_match_an_observed_source() -> None:
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "公司持有许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "https://regulator.example/licenses/ABC-123/",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "该链接与研究输出中的 URL 不完全一致。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_output(
            _request_json(), _research_output(), mappings_json, "2026-07-17"
        )
    )

    assert package["usable_evidence"] == []
    assert package["rejected_evidence"][0]["reason"] == "source_not_observed"
    assert package["coverage"][0]["status"] == "needs_verification"


def test_rejects_mapping_with_an_excerpt_missing_from_the_observed_source() -> None:
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "公司持有许可。",
                "key_excerpt": "unrelated assertion not present in the source",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "关键摘录未出现在来源观察中。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_output(
            _request_json(), _research_output(), mappings_json, "2026-07-17"
        )
    )

    assert package["usable_evidence"] == []
    assert package["rejected_evidence"][0]["reason"] == "excerpt_not_observed"
    assert package["coverage"][0]["status"] == "needs_verification"


def test_preserves_the_exact_observed_root_url_in_usable_evidence() -> None:
    research_output = """--- SOURCE 1: Root registry ---
URL: https://regulator.example

SUMMARY:
Registry entry says root-source excerpt.

--------------------------------------------------------------------------------
"""
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "root-source excerpt",
                "key_excerpt": "root-source excerpt",
                "source_url": "https://regulator.example",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_output(
            _request_json(),
            research_output,
            mappings_json,
            "2026-07-17",
            source_verifier=_verified_source,
        )
    )

    assert package["usable_evidence"][0]["source_url"] == "https://regulator.example"
    assert package["research_sources"][0]["source_url"] == "https://regulator.example"


def test_omits_research_sources_with_embedded_credentials() -> None:
    research_output = """--- SOURCE 1: Unsafe source ---
URL: https://user:secret@regulator.example/licenses/ABC-123

SUMMARY:
This source must not appear in a package.

--------------------------------------------------------------------------------
"""

    assert extract_research_sources(research_output, "2026-07-17") == []


def test_accepts_an_excerpt_from_any_observation_of_the_same_url() -> None:
    research_output = """--- SOURCE 1: Earlier observation ---
URL: https://regulator.example/licenses/ABC-123

SUMMARY:
Earlier observation contains licence excerpt ABC-123.

--------------------------------------------------------------------------------

--- SOURCE 2: Later observation ---
URL: https://regulator.example/licenses/ABC-123

SUMMARY:
Later observation contains different context.

--------------------------------------------------------------------------------
"""
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "licence excerpt ABC-123",
                "key_excerpt": "licence excerpt ABC-123",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_output(
            _request_json(),
            research_output,
            mappings_json,
            "2026-07-17",
            source_verifier=_verified_source,
        )
    )

    assert package["coverage"][0]["status"] == "covered"


def test_builds_evidence_from_a_platform_neutral_agent_research_record() -> None:
    research_record_json = json.dumps(
        {
            "agent": {"name": "Codex", "mode": "interactive"},
            "sources": [
                {
                    "title": "License registry",
                    "source_url": "https://regulator.example/licenses/ABC-123",
                    "research_excerpt": (
                        "Registry lists license ABC-123 for Example Company."
                    ),
                }
            ],
        }
    )
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "license ABC-123 for Example Company",
                "key_excerpt": "license ABC-123 for Example Company",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_record(
            _request_json(),
            research_record_json,
            mappings_json,
            "2026-07-17",
            source_verifier=_verified_source,
        )
    )

    assert package["coverage"][0]["status"] == "covered"
    assert package["research_sources"][0]["title"] == "License registry"


def test_omits_unsafe_urls_from_an_agent_research_record() -> None:
    research_record_json = json.dumps(
        {
            "agent": {"name": "Codex"},
            "sources": [
                {
                    "title": "Unsafe source",
                    "source_url": "https://user:secret@regulator.example/licenses/ABC-123",
                    "research_excerpt": "This source must not appear.",
                }
            ],
        }
    )

    package = json.loads(
        build_evidence_package_from_research_record(
            _request_json(), research_record_json, "[]", "2026-07-17"
        )
    )

    assert package["research_sources"] == []


def test_high_priority_external_agent_evidence_requires_page_verification() -> None:
    research_record_json = json.dumps(
        {
            "sources": [
                {
                    "title": "License registry",
                    "source_url": "https://regulator.example/licenses/ABC-123",
                    "research_excerpt": "Registry lists license ABC-123 for Example Company.",
                }
            ]
        }
    )
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "license ABC-123 for Example Company",
                "key_excerpt": "license ABC-123 for Example Company",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    unverified_package = json.loads(
        build_evidence_package_from_research_record(
            _request_json(), research_record_json, mappings_json, "2026-07-17"
        )
    )
    verified_package = json.loads(
        build_evidence_package_from_research_record(
            _request_json(),
            research_record_json,
            mappings_json,
            "2026-07-17",
            source_verifier=lambda _url, _excerpt: SourceVerification(
                status="verified", content_sha256="a" * 64
            ),
        )
    )

    assert unverified_package["coverage"][0]["status"] == "needs_verification"
    assert unverified_package["rejected_evidence"][0]["reason"] == "source_not_verified"
    assert verified_package["coverage"][0]["status"] == "covered"
    assert verified_package["source_verifications"][0]["content_sha256"] == "a" * 64


def test_high_priority_fact_must_be_the_verified_direct_quote() -> None:
    research_record_json = json.dumps(
        {
            "sources": [
                {
                    "title": "License registry",
                    "source_url": "https://regulator.example/licenses/ABC-123",
                    "research_excerpt": "Registry lists license ABC-123 for Example Company.",
                }
            ]
        }
    )
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "公司已获得所有必要许可。",
                "key_excerpt": "license ABC-123 for Example Company",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_record(
            _request_json(),
            research_record_json,
            mappings_json,
            "2026-07-17",
            source_verifier=_verified_source,
        )
    )

    assert package["coverage"][0]["status"] == "needs_verification"
    assert package["rejected_evidence"][0]["reason"] == "fact_not_direct_quote"


def test_public_source_fetcher_rejects_loopback_urls() -> None:
    verification = fetch_public_source(
        "http://127.0.0.1:9999/internal", "internal"
    )

    assert verification.status == "fetch_failed"


def test_public_source_fetcher_pins_the_verified_dns_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connected_to: list[tuple[str, int]] = []

    def fake_getaddrinfo(*_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

    def fake_create_connection(address: tuple[str, int], timeout: int) -> object:
        connected_to.append(address)
        raise OSError("stop before network")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    verification = fetch_public_source("https://example.test/source", "quote")

    assert verification.status == "fetch_failed"
    assert connected_to == [("93.184.216.34", 443)]


def test_public_source_fetcher_records_hash_for_pinned_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "open_deep_research.diligence_research_adapter._public_network_target",
        lambda _url: ("example.test", 443, "93.184.216.34"),
    )
    monkeypatch.setattr(
        "open_deep_research.diligence_research_adapter._fetch_pinned_public_content",
        lambda *_args: b"verified direct quote",
    )

    verification = fetch_public_source(
        "https://example.test/source", "verified direct quote"
    )

    assert verification.status == "verified"
    assert verification.fetched_at is not None
    assert verification.content_sha256 == (
        "85c94c76eb3f9f314c71dd9797fbfd8a250ea6bfe78c9db80ecd605864b18b22"
    )


def test_unverified_normal_priority_agent_evidence_is_not_usable() -> None:
    request_json = json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [{"id": "license", "statement": "许可", "priority": "normal"}],
        }
    )
    research_record_json = json.dumps(
        {
            "sources": [
                {
                    "title": "License registry",
                    "source_url": "https://regulator.example/licenses/ABC-123",
                    "research_excerpt": "license ABC-123 for Example Company",
                }
            ]
        }
    )
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "公司持有许可。",
                "key_excerpt": "license ABC-123 for Example Company",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在。",
            }
        ]
    )

    package = json.loads(
        build_evidence_package_from_research_record(
            request_json, research_record_json, mappings_json, "2026-07-20"
        )
    )

    assert package["usable_evidence"] == []
    assert package["coverage"][0]["status"] == "needs_verification"
    assert package["rejected_evidence"][0]["reason"] == "source_not_verified"
