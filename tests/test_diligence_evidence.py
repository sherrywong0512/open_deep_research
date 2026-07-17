"""Behavioral tests for the diligence evidence package seam."""

import json

from open_deep_research.diligence_evidence import build_evidence_package


def test_builds_usable_evidence_for_a_complete_candidate() -> None:
    request_json = json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [
                {
                    "id": "claim-1",
                    "statement": "公司持有某项许可",
                    "priority": "high",
                }
            ],
        }
    )
    candidates_json = json.dumps(
        [
            {
                "claim_id": "claim-1",
                "fact": "监管页面列示该公司持有许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "仅核验许可存在，不推断经营表现。",
            }
        ]
    )

    package = json.loads(build_evidence_package(request_json, candidates_json))

    assert package["usable_evidence"][0]["claim_id"] == "claim-1"
    assert package["rejected_evidence"] == []
    assert package["coverage"][0]["status"] == "covered"


def test_rejects_candidate_without_a_source_and_marks_claim_for_verification() -> None:
    request_json = json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [
                {
                    "id": "claim-1",
                    "statement": "公司持有某项许可",
                    "priority": "high",
                }
            ],
        }
    )
    candidates_json = json.dumps(
        [
            {
                "claim_id": "claim-1",
                "fact": "公司持有某项许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "company_website",
                "evidence_level": "C",
                "is_independent": False,
                "limitations": "只有公司自述。",
            }
        ]
    )

    package = json.loads(build_evidence_package(request_json, candidates_json))

    assert package["usable_evidence"] == []
    assert package["rejected_evidence"][0]["claim_id"] == "claim-1"
    assert "source_url" in package["rejected_evidence"][0]["missing_fields"]
    assert package["coverage"][0]["status"] == "needs_verification"
