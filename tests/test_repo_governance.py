"""Repository governance and docs asset checks."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_governance_guidance_files_exist() -> None:
    required = (
        "AGENTS.md",
        "CONTRIBUTING.md",
        ".governance-kit.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "docs/LLM-WIKI-PLAN.md",
    )
    missing = [path for path in required if not (REPO_ROOT / path).is_file()]
    assert not missing, f"Missing governance files: {', '.join(missing)}"


def test_raw_assets_markdown_has_no_trailing_whitespace() -> None:
    assets_dir = REPO_ROOT / "raw" / "assets"
    assert assets_dir.is_dir(), "raw/assets directory is missing"

    trailing = re.compile(r"[ \t]+$")
    violations: list[str] = []

    for path in sorted(assets_dir.glob("*.md")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if trailing.search(line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}")

    assert not violations, "Trailing whitespace found:\n" + "\n".join(violations)


def test_pr_contract_fetch_has_merge_base() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pr-contract.yml").read_text(
        encoding="utf-8"
    )
    assert 'git fetch origin "$BASE_REF" --depth=1' not in workflow
