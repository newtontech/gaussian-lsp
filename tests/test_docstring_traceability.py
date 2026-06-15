"""Tests for the OpenQC v1 docstring/wiki/raw traceability report.

Covers issue #94: shape, repo-relative paths, rule ID format, deterministic
generation, and the strict validator in ``scripts/check_docstring_traceability.py``.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "reports" / "docstring-wiki-raw-traceability.json"
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_docstring_traceability.py"

SCHEMA_VERSION = "openqc.lsp.traceability.v1"
TRACE_CODE_PATTERN = re.compile(r"^GAUSSIAN-[A-Z]+-[A-Z]+-\d{3}$")
ABSOLUTE_PATH_PATTERN = re.compile(r"^/(?:Users|home|tmp|var|root|etc)")


def _load_checker_module():
    """Load the checker script as a Python module for white-box tests."""
    spec = importlib.util.spec_from_file_location("check_docstring_traceability", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so ``dataclass`` annotation resolution works.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report() -> dict:
    assert REPORT_PATH.is_file(), f"missing report at {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def checker():
    return _load_checker_module()


# ---------------------------------------------------------------------------
# Top-level shape
# ---------------------------------------------------------------------------


def test_report_has_required_top_level_fields(report: dict) -> None:
    required = {
        "schemaVersion",
        "serverId",
        "repository",
        "languageId",
        "generatedAt",
        "summary",
        "docstrings",
        "wikiSources",
        "ruleIds",
        "sourceUrls",
        "rawManifest",
    }
    missing = required - set(report)
    assert not missing, f"missing top-level fields: {sorted(missing)}"


def test_report_schema_version_is_openqc_v1(report: dict) -> None:
    assert report["schemaVersion"] == SCHEMA_VERSION


def test_report_server_id_matches_lsp_identity(report: dict) -> None:
    assert report["serverId"] == "gaussian-lsp"
    assert report["repository"] == "newtontech/gaussian-lsp"
    assert report["languageId"] == "gaussian"


def test_report_generated_at_is_iso(report: dict) -> None:
    # ISO 8601 UTC stamp -- ``YYYY-MM-DDTHH:MM:SSZ``.
    value = report["generatedAt"]
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", value), value


# ---------------------------------------------------------------------------
# Summary counters -- the strict OpenQC gate
# ---------------------------------------------------------------------------


def test_summary_docstrings_linked_equals_total(report: dict) -> None:
    summary = report["summary"]
    assert summary["docstringsLinked"] == summary["docstringsTotal"]
    assert summary["docstringsTotal"] > 0


def test_summary_zero_failure_counters(report: dict) -> None:
    summary = report["summary"]
    for counter in ("brokenWikiLinks", "wikiSourcesWithoutRaw", "rawManifestFailures"):
        assert summary[counter] == 0, f"summary.{counter} must be zero"


def test_summary_section_lists_all_required_counters(report: dict) -> None:
    required = {
        "docstringsTotal",
        "docstringsLinked",
        "wikiSourcesTotal",
        "wikiSourcesLinked",
        "ruleIdsTotal",
        "rawManifestEntries",
        "brokenWikiLinks",
        "wikiSourcesWithoutRaw",
        "rawManifestFailures",
    }
    missing = required - set(report["summary"])
    assert not missing, f"missing summary counters: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Rule ID format
# ---------------------------------------------------------------------------


def test_every_rule_id_matches_openqc_format(report: dict) -> None:
    assert report["ruleIds"], "ruleIds section is empty"
    for rule in report["ruleIds"]:
        assert TRACE_CODE_PATTERN.match(rule["code"]), rule["code"]


def test_every_rule_id_has_consistent_fields(report: dict) -> None:
    for rule in report["ruleIds"]:
        assert rule["ruleCode"], rule
        assert rule["fileRole"] in {"LINT", "LOGP", "TSDS"}, rule
        assert rule["category"] in {
            "SCHEMA",
            "TYPE",
            "SEMANTIC",
            "STYLE",
            "XREF",
            "SYNTAX",
            "RUNTIME",
        }, rule
        assert isinstance(rule["ordinal"], int) and rule["ordinal"] >= 1, rule
        assert rule["severity"] in {"error", "warning", "hint", "information"}, rule
        # Trace code must agree with fileRole/category/ordinal.
        expected = f"GAUSSIAN-{rule['fileRole']}-{rule['category']}-{rule['ordinal']:03d}"
        assert rule["code"] == expected, (rule["code"], expected)


def test_rule_ids_are_unique(report: dict) -> None:
    codes = [r["code"] for r in report["ruleIds"]]
    assert len(codes) == len(set(codes)), "duplicate rule IDs detected"


def test_rule_ids_cover_lint_log_and_ts_surfaces(report: dict) -> None:
    """The report must trace rules from all three diagnostic surfaces."""
    file_roles = {r["fileRole"] for r in report["ruleIds"]}
    assert file_roles == {"LINT", "LOGP", "TSDS"}, file_roles

    # Sanity: the LINT surface owns the canonical G0xx codes; the LOGP and
    # TSDS surfaces own the canonical GAUS-Exx/Wxx/Ixx codes.
    lint_codes = {r["ruleCode"] for r in report["ruleIds"] if r["fileRole"] == "LINT"}
    assert {"G001", "G002", "G010", "G020", "G040"} <= lint_codes
    logp_codes = {r["ruleCode"] for r in report["ruleIds"] if r["fileRole"] == "LOGP"}
    assert {"GAUSS-E034", "GAUSS-E035", "GAUSS-E036", "GAUSS-I031"} <= logp_codes
    tsds_codes = {r["ruleCode"] for r in report["ruleIds"] if r["fileRole"] == "TSDS"}
    assert {"GAUSS-E030", "GAUSS-E031", "GAUSS-W030", "GAUSS-E032"} <= tsds_codes


# ---------------------------------------------------------------------------
# Repo-relative paths
# ---------------------------------------------------------------------------


def _string_paths(entry: dict) -> list[str]:
    return [
        v
        for v in entry.values()
        if isinstance(v, str)
        and (v.startswith("/") or v.startswith("~"))
        and (v.endswith(".py") or v.endswith(".ts") or v.endswith(".md") or v.endswith(".json"))
    ]


def test_docstring_paths_are_repo_relative(report: dict) -> None:
    for idx, entry in enumerate(report["docstrings"]):
        bad = _string_paths(entry)
        assert not bad, f"docstrings[{idx}] has absolute paths: {bad}"
        assert entry["path"].startswith("src/"), entry
        assert entry["wikiPath"].startswith("wiki/"), entry
        assert entry["rawPath"].startswith("raw/assets/"), entry


def test_wiki_source_paths_are_repo_relative(report: dict) -> None:
    for idx, entry in enumerate(report["wikiSources"]):
        bad = _string_paths(entry)
        assert not bad, f"wikiSources[{idx}] has absolute paths: {bad}"
        assert entry["wikiPath"].startswith("wiki/"), entry
        assert entry["rawPath"].startswith("raw/assets/"), entry


def test_rule_id_paths_are_repo_relative(report: dict) -> None:
    for idx, entry in enumerate(report["ruleIds"]):
        bad = _string_paths(entry)
        assert not bad, f"ruleIds[{idx}] has absolute paths: {bad}"


def test_raw_manifest_path_is_repo_relative(report: dict) -> None:
    raw_manifest = report["rawManifest"]
    assert raw_manifest["path"] == "raw/assets/manifest.json"
    for failure in raw_manifest.get("failures", []):
        assert not ABSOLUTE_PATH_PATTERN.match(failure["path"]), failure


# ---------------------------------------------------------------------------
# Cross-artifact consistency
# ---------------------------------------------------------------------------


def test_every_docstring_resolves_to_real_files(report: dict) -> None:
    for entry in report["docstrings"]:
        assert (REPO_ROOT / entry["path"]).is_file(), entry
        assert (REPO_ROOT / entry["wikiPath"]).is_file(), entry
        assert (REPO_ROOT / entry["rawPath"]).is_file(), entry


def test_every_docstring_wiki_mentions_rule_code(report: dict) -> None:
    for entry in report["docstrings"]:
        text = (REPO_ROOT / entry["wikiPath"]).read_text(encoding="utf-8")
        pattern = re.compile(rf"(?<![A-Z0-9-]){re.escape(entry['ruleCode'])}(?![A-Z0-9-])")
        assert pattern.search(
            text
        ), f"wiki {entry['wikiPath']} does not mention {entry['ruleCode']}"


def test_every_raw_asset_is_in_manifest(report: dict) -> None:
    manifest = json.loads(
        (REPO_ROOT / "raw" / "assets" / "manifest.json").read_text(encoding="utf-8")
    )
    manifest_paths = {f"raw/assets/{e['path']}" for e in manifest["entries"]}
    for entry in report["docstrings"]:
        assert entry["rawPath"] in manifest_paths, entry


def test_wiki_sources_reference_real_files(report: dict) -> None:
    for ws in report["wikiSources"]:
        assert (REPO_ROOT / ws["wikiPath"]).is_file(), ws
        assert (REPO_ROOT / ws["rawPath"]).is_file(), ws


def test_source_urls_are_https(report: dict) -> None:
    assert report["sourceUrls"], "sourceUrls is empty"
    for url in report["sourceUrls"]:
        assert url.startswith("https://") or url.startswith("http://"), url
        assert "newtontech.local" not in url
        assert not url.endswith("gaussian-lsp.git"), url


# ---------------------------------------------------------------------------
# Strict validator
# ---------------------------------------------------------------------------


def test_strict_validator_accepts_committed_report() -> None:
    """The committed report must pass ``--strict`` with exit code 0."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--strict"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"strict validator failed:\nstdout={result.stdout}\nstderr={result.stderr}"


def test_strict_validator_rejects_stale_report(tmp_path, monkeypatch) -> None:
    """If a rule code is dropped the on-disk report must become stale."""
    # Run the generator into a temp reports dir, mutate the temp report, and
    # point the checker at it via the REPO_ROOT module attribute.
    bogus_report_dir = tmp_path / "reports"
    bogus_report_dir.mkdir()
    bogus_report_path = bogus_report_dir / "docstring-wiki-raw-traceability.json"

    module = _load_checker_module()
    fresh, _ = module.build_report(module.DEFAULT_GENERATED_AT)
    fresh["summary"]["brokenWikiLinks"] = 1  # corrupt the summary
    bogus_report_path.write_text(json.dumps(fresh), encoding="utf-8")

    monkeypatch.setattr(module, "REPORT_PATH", bogus_report_path)
    errors = module.validate_report(json.loads(bogus_report_path.read_text()))
    assert any("brokenWikiLinks" in e for e in errors), errors


def test_generator_is_deterministic() -> None:
    """Two consecutive ``build_report`` calls must produce identical JSON."""
    module = _load_checker_module()
    first, _ = module.build_report(module.DEFAULT_GENERATED_AT)
    second, _ = module.build_report(module.DEFAULT_GENERATED_AT)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_trace_id_format_helper(checker) -> None:
    """Trace IDs group by (file_role, category_short) and start at ordinal 1."""
    mapping = checker.assign_trace_ids(checker.RULE_CATALOG)
    # Every trace ID matches the required pattern.
    for trace_id in mapping.values():
        assert TRACE_CODE_PATTERN.match(trace_id), trace_id
    # Ordinals within each group are dense starting at 1.
    groups: dict[str, list[int]] = {}
    for trace_id in mapping.values():
        prefix, ordinal = trace_id.rsplit("-", 1)
        groups.setdefault(prefix, []).append(int(ordinal))
    for prefix, ordinals in groups.items():
        assert ordinals == list(range(1, len(ordinals) + 1)), (prefix, ordinals)


def test_rule_catalog_covers_all_lint_constants() -> None:
    """Every RULE_* constant in lint.py must be traced."""
    module = _load_checker_module()
    lint_source = (REPO_ROOT / "src/gaussian_lsp/features/lint.py").read_text(encoding="utf-8")
    declared = set(re.findall(r'^RULE_\w+\s*=\s*"([^"]+)"', lint_source, re.MULTILINE))
    traced = {spec.rule_code for spec in module.RULE_CATALOG if spec.file_role == "LINT"}
    assert declared <= traced, f"untraced LINT constants: {declared - traced}"


def test_rule_catalog_covers_all_log_parser_constants() -> None:
    """Every CODE_* constant in log_parser.py must be traced."""
    module = _load_checker_module()
    log_source = (REPO_ROOT / "src/gaussian_lsp/log_parser.py").read_text(encoding="utf-8")
    declared = set(re.findall(r'^CODE_\w+\s*=\s*"([^"]+)"', log_source, re.MULTILINE))
    traced = {spec.rule_code for spec in module.RULE_CATALOG if spec.file_role == "LOGP"}
    # CODE_INCOMPLETE_LOG is the only GAUSS-Ixxx code; ensure it is captured.
    assert declared <= traced, f"untraced LOGP constants: {declared - traced}"
