"""Build traceable evidence packages for public-information diligence."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ValidationError


class DiligenceClaim(BaseModel):
    """Describe one public-information claim that needs verification."""

    id: str
    statement: str
    priority: Literal["high", "normal"] = "normal"


class DiligenceRequest(BaseModel):
    """Define the scope for one diligence evidence package."""

    subject: str
    purpose: str
    claims: list[DiligenceClaim]


class EvidenceCandidate(BaseModel):
    """Represent one source-backed factual candidate."""

    claim_id: str
    fact: str
    key_excerpt: str
    source_url: str
    published_at: str
    accessed_at: str
    source_type: str
    evidence_level: Literal["A", "B", "C", "U"]
    is_independent: bool
    limitations: str


_REQUIRED_CANDIDATE_FIELDS = (
    "claim_id",
    "fact",
    "key_excerpt",
    "source_url",
    "published_at",
    "accessed_at",
    "source_type",
    "evidence_level",
    "is_independent",
    "limitations",
)


def build_evidence_package(request_json: str, candidates_json: str) -> str:
    """Validate candidate evidence and return a JSON diligence evidence package."""
    request = DiligenceRequest.model_validate_json(request_json)
    raw_candidates = json.loads(candidates_json)
    if not isinstance(raw_candidates, list):
        raise ValueError("candidates_json must contain a JSON array")

    claim_ids = {claim.id for claim in request.claims}
    usable_evidence: list[dict[str, Any]] = []
    rejected_evidence: list[dict[str, Any]] = []

    for raw_candidate in raw_candidates:
        candidate_data = raw_candidate if isinstance(raw_candidate, dict) else {}
        claim_id = candidate_data.get("claim_id")
        missing_fields = _missing_fields(candidate_data)

        if missing_fields:
            rejected_evidence.append(
                {
                    "claim_id": claim_id,
                    "missing_fields": missing_fields,
                    "reason": "missing_required_fields",
                }
            )
            continue

        try:
            candidate = EvidenceCandidate.model_validate(candidate_data)
        except ValidationError:
            rejected_evidence.append(
                {
                    "claim_id": claim_id,
                    "missing_fields": missing_fields,
                    "reason": "invalid_candidate",
                }
            )
            continue

        if candidate.claim_id not in claim_ids:
            rejected_evidence.append(
                {
                    "claim_id": candidate.claim_id,
                    "missing_fields": [],
                    "reason": "unknown_claim",
                }
            )
            continue

        usable_evidence.append(candidate.model_dump(mode="json"))

    coverage = _coverage_for(request, usable_evidence)
    open_verification_items = [
        {
            "claim_id": item["claim_id"],
            "statement": item["statement"],
            "reason": "missing_independent_A_or_B_evidence"
            if item["priority"] == "high"
            else "missing_usable_evidence",
        }
        for item in coverage
        if item["status"] == "needs_verification"
    ]

    return json.dumps(
        {
            "subject": request.subject,
            "purpose": request.purpose,
            "usable_evidence": usable_evidence,
            "rejected_evidence": rejected_evidence,
            "coverage": coverage,
            "open_verification_items": open_verification_items,
        },
        ensure_ascii=False,
    )


def _missing_fields(candidate: dict[str, Any]) -> list[str]:
    """List required fields that are absent or empty."""
    return [
        field
        for field in _REQUIRED_CANDIDATE_FIELDS
        if field not in candidate or candidate[field] in (None, "")
    ]


def _coverage_for(
    request: DiligenceRequest, usable_evidence: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Report whether every requested claim has sufficient usable evidence."""
    coverage: list[dict[str, str]] = []
    for claim in request.claims:
        claim_evidence = [
            item for item in usable_evidence if item["claim_id"] == claim.id
        ]
        has_independent_primary_evidence = any(
            item["is_independent"] and item["evidence_level"] in {"A", "B"}
            for item in claim_evidence
        )
        is_covered = bool(claim_evidence) and (
            claim.priority != "high" or has_independent_primary_evidence
        )
        coverage.append(
            {
                "claim_id": claim.id,
                "statement": claim.statement,
                "priority": claim.priority,
                "status": "covered" if is_covered else "needs_verification",
            }
        )
    return coverage
