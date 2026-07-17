"""Behavioral tests for converting research-tool output into evidence packages."""

import json

from open_deep_research.diligence_research_adapter import (
    build_evidence_package_from_research_output,
    extract_research_sources,
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


def test_builds_evidence_only_when_mapping_points_to_observed_source() -> None:
    mappings_json = json.dumps(
        [
            {
                "claim_id": "license",
                "fact": "监管登记页列示 Example Company 持有许可。",
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
            _request_json(), _research_output(), mappings_json, "2026-07-17"
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
                "fact": "监管登记页列示公司持有许可。",
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
            _request_json(), research_output, mappings_json, "2026-07-17"
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
                "fact": "监管登记页列示公司持有许可。",
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
            _request_json(), research_output, mappings_json, "2026-07-17"
        )
    )

    assert package["coverage"][0]["status"] == "covered"
