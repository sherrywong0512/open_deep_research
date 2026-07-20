"""Behavioral tests for the diligence evidence package seam."""

import json

from open_deep_research.diligence_evidence import build_candidate_package


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

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"][0]["claim_id"] == "claim-1"
    assert package["rejected_evidence"] == []
    assert package["coverage"][0]["status"] == "needs_verification"
    assert "verified_candidates" not in package
    assert "human_review_items" not in package


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

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"] == []
    assert package["rejected_evidence"][0]["claim_id"] == "claim-1"
    assert "source_url" in package["rejected_evidence"][0]["missing_fields"]
    assert package["coverage"][0]["status"] == "needs_verification"


def test_rejects_candidate_with_an_empty_source_url() -> None:
    request_json = json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [{"id": "claim-1", "statement": "公司持有某项许可"}],
        }
    )
    candidates_json = json.dumps(
        [
            {
                "claim_id": "claim-1",
                "fact": "公司持有某项许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "来源链接为空，无法复核。",
            }
        ]
    )

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"] == []
    assert package["rejected_evidence"][0]["missing_fields"] == ["source_url"]
    assert package["coverage"][0]["status"] == "needs_verification"


def test_rejects_candidate_with_a_whitespace_only_source_url() -> None:
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
                "source_url": "   ",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "来源链接为空白，无法复核。",
            }
        ]
    )

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"] == []
    assert package["rejected_evidence"][0]["missing_fields"] == ["source_url"]
    assert package["coverage"][0]["status"] == "needs_verification"


def test_rejects_candidate_with_an_invalid_source_url_or_date() -> None:
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
                "source_url": "not-a-url",
                "published_at": "unknown",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "来源链接和发布日期均不可复核。",
            }
        ]
    )

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"] == []
    assert package["rejected_evidence"][0]["reason"] == "invalid_candidate"
    assert package["coverage"][0]["status"] == "needs_verification"


def test_rejects_candidate_with_a_datetime_instead_of_an_iso_date() -> None:
    request_json = json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [{"id": "claim-1", "statement": "公司持有某项许可"}],
        }
    )
    candidates_json = json.dumps(
        [
            {
                "claim_id": "claim-1",
                "fact": "公司持有某项许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "https://regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10T00:00:00Z",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "发布日期含时间，不能按日期契约无声截断。",
            }
        ]
    )

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"] == []
    assert package["rejected_evidence"][0]["reason"] == "invalid_candidate"
    assert package["coverage"][0]["status"] == "needs_verification"


def test_rejects_source_urls_without_a_host_with_credentials_or_invalid_ports() -> None:
    request_json = json.dumps(
        {
            "subject": "Example Company",
            "purpose": "会前公开信息核验",
            "claims": [{"id": "claim-1", "statement": "公司持有某项许可"}],
        }
    )
    candidates_json = json.dumps(
        [
            {
                "claim_id": "claim-1",
                "fact": "公司持有某项许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "https://user@",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "无效来源。",
            },
            {
                "claim_id": "claim-1",
                "fact": "公司持有某项许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "https://user:secret@regulator.example/licenses/ABC-123",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "来源包含凭据。",
            },
            {
                "claim_id": "claim-1",
                "fact": "公司持有某项许可。",
                "key_excerpt": "许可证编号：ABC-123",
                "source_url": "https://regulator.example:invalid/licenses/ABC-123",
                "published_at": "2026-01-10",
                "accessed_at": "2026-07-17",
                "source_type": "regulatory_record",
                "evidence_level": "A",
                "is_independent": True,
                "limitations": "端口无效。",
            },
        ]
    )

    package = json.loads(build_candidate_package(request_json, candidates_json))

    assert package["candidate_evidence"] == []
    assert len(package["rejected_evidence"]) == 3
    assert package["coverage"][0]["status"] == "needs_verification"
