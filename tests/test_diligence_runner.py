"""End-to-end tests for the diligence evidence command-line runner."""

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


@pytest.fixture
def page_url() -> str:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = b"Registry lists license ABC-123 for Example Company."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/license"
    finally:
        server.shutdown()
        thread.join()


def test_runner_writes_a_grounded_evidence_package(
    tmp_path: Path, page_url: str
) -> None:
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
        f"""--- SOURCE 1: License registry ---
URL: {page_url}

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
                    "fact": "license ABC-123 for Example Company",
                    "key_excerpt": "license ABC-123 for Example Company",
                    "source_url": page_url,
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
    assert package["coverage"][0]["status"] == "needs_verification"
    assert package["rejected_evidence"][0]["reason"] == "source_not_verified"


def test_runner_accepts_a_platform_neutral_agent_research_record(
    tmp_path: Path, page_url: str
) -> None:
    request_path = tmp_path / "request.json"
    research_path = tmp_path / "research-record.json"
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
        json.dumps(
            {
                "agent": {"name": "Codex", "mode": "interactive"},
                "sources": [
                    {
                        "title": "License registry",
                        "source_url": page_url,
                        "research_excerpt": (
                            "Registry lists license ABC-123 for Example Company."
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    mappings_path.write_text(
        json.dumps(
            [
                {
                    "claim_id": "license",
                    "fact": "license ABC-123 for Example Company",
                    "key_excerpt": "license ABC-123 for Example Company",
                    "source_url": page_url,
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
            "--research-record",
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
    assert package["coverage"][0]["status"] == "needs_verification"
    assert package["rejected_evidence"][0]["reason"] == "source_not_verified"


def test_runner_executes_the_documented_codex_example(tmp_path: Path) -> None:
    repository_root = Path(__file__).parents[1]
    output_path = tmp_path / "package.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "open_deep_research.diligence_runner",
            "--request",
            str(repository_root / "examples/due_diligence_request.json"),
            "--research-record",
            str(repository_root / "examples/codex_research_record.json"),
            "--mappings",
            str(repository_root / "examples/due_diligence_mappings.json"),
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
    assert package["coverage"][0]["claim_id"] == "licence-exists"
    assert package["coverage"][0]["status"] == "needs_verification"
