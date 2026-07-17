"""End-to-end tests for the diligence evidence command-line runner."""

import json
import subprocess
import sys
from pathlib import Path


def test_runner_writes_a_grounded_evidence_package(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    research_path = tmp_path / "research.txt"
    mappings_path = tmp_path / "mappings.json"
    output_path = tmp_path / "package.json"
    request_path.write_text(
        json.dumps(
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
        ),
        encoding="utf-8",
    )
    research_path.write_text(
        """--- SOURCE 1: License registry ---
URL: https://regulator.example/licenses/ABC-123

SUMMARY:
Registry lists license ABC-123 for Example Company.

--------------------------------------------------------------------------------
""",
        encoding="utf-8",
    )
    mappings_path.write_text(
        json.dumps(
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
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "open_deep_research.diligence_runner",
            "--request",
            str(request_path),
            "--research-output",
            str(research_path),
            "--mappings",
            str(mappings_path),
            "--accessed-at",
            "2026-07-17",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    package = json.loads(output_path.read_text(encoding="utf-8"))
    assert package["coverage"][0]["status"] == "covered"
    assert package["usable_evidence"][0]["accessed_at"] == "2026-07-17"
