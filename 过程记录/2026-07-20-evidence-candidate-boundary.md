# Evidence candidate boundary

## Why

The initial evidence runner could independently re-fetch a source and verify a
quote, but it still reported `covered` from agent-supplied source grades and a
mapping. That overstates what a retrieval check proves: a quote can be real yet
irrelevant to the claim, and an agent cannot authoritatively grade a source.

## Change

- A successful quote check now produces `needs_human_review`, never an automatic
  business or diligence conclusion.
- The output relabels input `source_type`, `evidence_level`, and
  `is_independent` as a proposed `source_assessment`.
- The package emits a per-claim human-review item requiring confirmation that
  the quote supports the claim and that the source assessment is appropriate.
- Static HTML visible text and gzip-compressed static HTML are now supported;
  scripts, styles, redirects, private URLs, JavaScript rendering, PDFs, and
  unsupported encodings remain outside the technical boundary.

## Verification

- Red-to-green behavior tests: `26 passed` from
  `uv run pytest tests/test_diligence_evidence.py tests/test_diligence_research_adapter.py tests/test_diligence_runner.py -q -p no:cacheprovider`.
- `ruff` passed on the changed runner, evidence modules, and tests.
- `mypy` passed on the three diligence source modules.
- Public-source smoke test on 2026-07-20 used the upstream raw README at
  `https://raw.githubusercontent.com/langchain-ai/open_deep_research/main/README.md`.
  The runner independently fetched its quote, recorded
  `fetched_at=2026-07-20T14:24:26.408890+00:00` and raw-response SHA-256
  `0fc75629079c025b0200e6032a038edf9c91c332d4ce925cbc6165910008267f`, then
  returned `needs_human_review` with one review item. No page body was stored.

## Remaining boundary

This is a code-enforced evidence-candidate gate, not a trusted identity or
legal-adjudication system. A reviewer must still evaluate source authority,
semantic support, conflicts, and any inaccessible or dynamic source.
