"""Command-line runner for grounded diligence evidence packages."""

import argparse
import sys
from pathlib import Path
from typing import Sequence

from open_deep_research.diligence_research_adapter import (
    build_evidence_package_from_research_output,
    build_evidence_package_from_research_record,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Read a scoped request, research output, and mappings into an evidence package."""
    parser = argparse.ArgumentParser(
        description="Build a diligence evidence package from grounded research sources."
    )
    parser.add_argument("--request", type=Path, required=True)
    research_input = parser.add_mutually_exclusive_group(required=True)
    research_input.add_argument(
        "--research-output",
        type=Path,
        help="Built-in Tavily SOURCE / URL / SUMMARY output.",
    )
    research_input.add_argument(
        "--research-record",
        type=Path,
        help="Provider-neutral JSON record from Codex or another research agent.",
    )
    parser.add_argument("--mappings", type=Path, required=True)
    parser.add_argument("--accessed-at", required=True, help="ISO date: YYYY-MM-DD")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    request_json = args.request.read_text(encoding="utf-8")
    mappings_json = args.mappings.read_text(encoding="utf-8")
    if args.research_record:
        package = build_evidence_package_from_research_record(
            request_json,
            args.research_record.read_text(encoding="utf-8"),
            mappings_json,
            args.accessed_at,
        )
    else:
        package = build_evidence_package_from_research_output(
            request_json,
            args.research_output.read_text(encoding="utf-8"),
            mappings_json,
            args.accessed_at,
        )
    if args.output:
        args.output.write_text(f"{package}\n", encoding="utf-8")
    else:
        sys.stdout.write(f"{package}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
