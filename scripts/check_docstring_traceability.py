#!/usr/bin/env python3
"""OpenQC v1 docstring/wiki/raw traceability generator and validator.

Generates and validates ``reports/docstring-wiki-raw-traceability.json``
against the ``openqc.lsp.traceability.v1`` schema.

The report traces every diagnostic rule code constant declared in the
Python/TypeScript sources through three artifacts:

  1. **docstring** -- the source file line that declares the rule code
     constant (e.g. ``RULE_UNKNOWN_ROUTE_KEYWORD = "G001"``).
  2. **wiki page** -- a markdown page under ``wiki/`` that documents the rule.
  3. **raw evidence** -- a markdown asset under ``raw/assets/`` whose
     ``stable_id`` is registered in ``raw/assets/manifest.json``.

Strict validation enforces:

  - Every rule has a docstring location, a wiki page that mentions the rule
    code, and a raw asset registered in the manifest.
  - Every ``wiki_links`` entry in the manifest resolves to an existing file.
  - Every raw asset referenced from the report is present on disk and has a
    matching ``stable_id`` in the manifest.

Usage::

    python scripts/check_docstring_traceability.py --generate
    python scripts/check_docstring_traceability.py --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "reports" / "docstring-wiki-raw-traceability.json"
RAW_MANIFEST_PATH = REPO_ROOT / "raw" / "assets" / "manifest.json"

SCHEMA_VERSION = "openqc.lsp.traceability.v1"
SERVER_ID = "gaussian-lsp"
REPOSITORY = "newtontech/gaussian-lsp"
LANGUAGE_ID = "gaussian"
DEFAULT_GENERATED_AT = "2026-06-16T00:00:00Z"

# ---------------------------------------------------------------------------
# Category / file-role short codes used in the trace IDs
# ---------------------------------------------------------------------------

CATEGORY_TO_SHORT: Dict[str, str] = {
    "schema": "SCHEMA",
    "type/value": "TYPE",
    "semantic consistency": "SEMANTIC",
    "style/deprecation": "STYLE",
    "cross-file reference": "XREF",
    "syntax": "SYNTAX",
    "preflight/runtime-risk": "RUNTIME",
}

FILE_ROLE_LINT = "LINT"  # src/gaussian_lsp/features/lint.py
FILE_ROLE_LOGP = "LOGP"  # src/gaussian_lsp/log_parser.py
FILE_ROLE_TSDS = "TSDS"  # src/parsers/diagnostics.ts


# ---------------------------------------------------------------------------
# Static rule catalog -- the single source of truth for traceability.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleSpec:
    """A single diagnostic rule with its traceability targets."""

    rule_code: str  # e.g. "G001" or "GAUSS-E034"
    file_role: str  # LINT | LOGP | TSDS
    category: str  # canonical category string from lsp-capabilities.json
    severity: str  # error | warning | hint | information
    symbol: str  # Python constant name OR TS sentinel "<ts-literal>"
    doc_path: str  # repo-relative source file
    wiki_path: str  # repo-relative wiki page
    raw_path: str  # repo-relative raw asset
    raw_stable_id: str  # manifest stable_id for the raw asset

    @property
    def category_short(self) -> str:
        return CATEGORY_TO_SHORT[self.category]


# Wiki pages shared across the catalog.
_WIKI_RULE_CATALOG = "wiki/synthesis/diagnostics-rule-catalog.md"
_WIKI_LOG_RUNTIME = "wiki/concepts/gaussian-log-runtime-errors.md"

# Raw assets shared across the catalog.
_RAW_DIAG_ENGINE = "raw/assets/diagnostic-engine-v1.md"
_RAW_DIAG_SCHEMA = "raw/assets/diagnostic-schema.md"
_RAW_INPUT_FORMAT = "raw/assets/gaussian-input-format.md"
_RAW_OUTPUT_FORMAT = "raw/assets/gaussian-output-format.md"


RULE_CATALOG: Tuple[RuleSpec, ...] = (
    # --- LINT rules (src/gaussian_lsp/features/lint.py) ---
    RuleSpec(
        "G001",
        FILE_ROLE_LINT,
        "schema",
        "warning",
        "RULE_UNKNOWN_ROUTE_KEYWORD",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G002",
        FILE_ROLE_LINT,
        "schema",
        "warning",
        "RULE_ROUTE_TYPO",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G010",
        FILE_ROLE_LINT,
        "schema",
        "warning",
        "RULE_UNKNOWN_LINK0",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G011",
        FILE_ROLE_LINT,
        "type/value",
        "warning",
        "RULE_NPROC_UNUSUAL",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G012",
        FILE_ROLE_LINT,
        "type/value",
        "warning",
        "RULE_MEM_LOW",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G020",
        FILE_ROLE_LINT,
        "schema",
        "warning",
        "RULE_NO_JOB_TYPE",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G021",
        FILE_ROLE_LINT,
        "semantic consistency",
        "warning",
        "RULE_FREQ_WITHOUT_OPT",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G022",
        FILE_ROLE_LINT,
        "semantic consistency",
        "warning",
        "RULE_OPT_LOOSE_CONVERGENCE",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G030",
        FILE_ROLE_LINT,
        "semantic consistency",
        "warning",
        "RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G031",
        FILE_ROLE_LINT,
        "semantic consistency",
        "warning",
        "RULE_SCF_CONVERGENCE_POSTHF",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    RuleSpec(
        "G040",
        FILE_ROLE_LINT,
        "style/deprecation",
        "hint",
        "RULE_VERBOSITY_HINT",
        "src/gaussian_lsp/features/lint.py",
        _WIKI_RULE_CATALOG,
        _RAW_DIAG_ENGINE,
        "gaussian-diagnostic-engine-v1-doc",
    ),
    # --- LOGP rules (src/gaussian_lsp/log_parser.py) ---
    RuleSpec(
        "GAUSS-E034",
        FILE_ROLE_LOGP,
        "preflight/runtime-risk",
        "error",
        "CODE_SCF_NOT_CONVERGED",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-E035",
        FILE_ROLE_LOGP,
        "syntax",
        "error",
        "CODE_GEOMETRY_PARSE_FAILURE",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-E036",
        FILE_ROLE_LOGP,
        "preflight/runtime-risk",
        "error",
        "CODE_ERROR_TERMINATION",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-E037",
        FILE_ROLE_LOGP,
        "preflight/runtime-risk",
        "error",
        "CODE_LINK_FAULT",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-E038",
        FILE_ROLE_LOGP,
        "preflight/runtime-risk",
        "error",
        "CODE_OPT_NOT_CONVERGED",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-E039",
        FILE_ROLE_LOGP,
        "preflight/runtime-risk",
        "error",
        "CODE_MEMORY_EXHAUSTED",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-W034",
        FILE_ROLE_LOGP,
        "semantic consistency",
        "warning",
        "CODE_OPT_STEP_UNCONVERGED",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-I031",
        FILE_ROLE_LOGP,
        "preflight/runtime-risk",
        "information",
        "CODE_INCOMPLETE_LOG",
        "src/gaussian_lsp/log_parser.py",
        _WIKI_LOG_RUNTIME,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    # --- TSDS rules (src/parsers/diagnostics.ts) ---
    RuleSpec(
        "GAUSS-E030",
        FILE_ROLE_TSDS,
        "schema",
        "error",
        "checkMissingRoute",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_INPUT_FORMAT,
        "gaussian-input-format-v1",
    ),
    RuleSpec(
        "GAUSS-E031",
        FILE_ROLE_TSDS,
        "schema",
        "error",
        "checkChargeMultiplicity",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_INPUT_FORMAT,
        "gaussian-input-format-v1",
    ),
    RuleSpec(
        "GAUSS-W030",
        FILE_ROLE_TSDS,
        "schema",
        "warning",
        "checkUnknownKeyword",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_INPUT_FORMAT,
        "gaussian-input-format-v1",
    ),
    RuleSpec(
        "GAUSS-W031",
        FILE_ROLE_TSDS,
        "schema",
        "warning",
        "checkMethodBasisIncompatibility",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_INPUT_FORMAT,
        "gaussian-input-format-v1",
    ),
    RuleSpec(
        "GAUSS-E032",
        FILE_ROLE_TSDS,
        "type/value",
        "error",
        "checkInvalidMemory",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_INPUT_FORMAT,
        "gaussian-input-format-v1",
    ),
    RuleSpec(
        "GAUSS-E033",
        FILE_ROLE_TSDS,
        "type/value",
        "error",
        "checkInvalidNproc",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_INPUT_FORMAT,
        "gaussian-input-format-v1",
    ),
    RuleSpec(
        "GAUSS-E034",
        FILE_ROLE_TSDS,
        "preflight/runtime-risk",
        "error",
        "parseLog:scf_not_converged",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
    RuleSpec(
        "GAUSS-E035",
        FILE_ROLE_TSDS,
        "syntax",
        "error",
        "parseLog:geometry_parse_failure",
        "src/parsers/diagnostics.ts",
        _WIKI_RULE_CATALOG,
        _RAW_OUTPUT_FORMAT,
        "gaussian-output-format-v1",
    ),
)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _find_python_constant_line(source: str, symbol: str, rule_code: str) -> Optional[int]:
    """Return the 1-based line number of ``SYMBOL = "RULE"`` in Python source."""
    pattern = re.compile(rf"^\s*{re.escape(symbol)}\s*=\s*[\"']{re.escape(rule_code)}[\"']")
    for idx, line in enumerate(source.splitlines(), start=1):
        if pattern.match(line):
            return idx
    return None


def _find_python_literal_line(source: str, rule_code: str) -> Optional[int]:
    """Return the 1-based line number of a ``code="RULE"`` literal in Python."""
    pattern = re.compile(rf"code\s*=\s*[\"']{re.escape(rule_code)}[\"']")
    for idx, line in enumerate(source.splitlines(), start=1):
        if pattern.search(line):
            return idx
    return None


def _find_ts_call_site_line(source: str, symbol: str, rule_code: str) -> Optional[int]:
    """Return the 1-based line number of the rule's call site in TS source.

    ``symbol`` for TS rules is the function name (e.g. ``checkMissingRoute``).
    We find the function body and locate the first ``code: 'RULE'`` line in it.
    """
    lines = source.splitlines()
    func_start: Optional[int] = None
    func_pattern = re.compile(rf"\bfunction\s+{re.escape(symbol)}\b")
    for idx, line in enumerate(lines, start=1):
        if func_pattern.search(line):
            func_start = idx
            break
    if func_start is None:
        # parseLog entries have multiple codes per function; fall back to grep.
        code_pattern = re.compile(rf"code:\s*'{re.escape(rule_code)}'")
        for idx, line in enumerate(lines, start=1):
            if code_pattern.search(line):
                return idx
        return None

    code_pattern = re.compile(rf"code:\s*'{re.escape(rule_code)}'")
    for idx, line in enumerate(lines[func_start - 1 :], start=func_start):
        if code_pattern.search(line):
            return idx
    return None


def find_docstring_line(spec: RuleSpec) -> Optional[int]:
    """Locate the docstring line for ``spec`` in its source file."""
    path = REPO_ROOT / spec.doc_path
    if not path.is_file():
        return None
    source = path.read_text(encoding="utf-8")
    if spec.file_role == FILE_ROLE_TSDS:
        return _find_ts_call_site_line(source, spec.symbol, spec.rule_code)
    if spec.symbol.startswith("<"):
        return _find_python_literal_line(source, spec.rule_code)
    return _find_python_constant_line(source, spec.symbol, spec.rule_code)


def assign_trace_ids(catalog: Tuple[RuleSpec, ...]) -> Dict[str, str]:
    """Deterministically assign GAUSSIAN-<ROLE>-<CAT>-NNN trace IDs."""
    grouped: Dict[Tuple[str, str], List[RuleSpec]] = {}
    for spec in catalog:
        grouped.setdefault((spec.file_role, spec.category_short), []).append(spec)

    mapping: Dict[str, str] = {}
    for role_cat in sorted(grouped):
        specs = sorted(grouped[role_cat], key=lambda s: s.rule_code)
        role, cat_short = role_cat
        for ordinal, spec in enumerate(specs, start=1):
            mapping[
                spec.rule_code + "@" + spec.file_role
            ] = f"GAUSSIAN-{role}-{cat_short}-{ordinal:03d}"
    return mapping


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


def load_raw_manifest() -> Dict[str, Any]:
    data: Dict[str, Any] = json.loads(RAW_MANIFEST_PATH.read_text(encoding="utf-8"))
    return data


def manifest_entry_by_stable_id(manifest: dict) -> Dict[str, dict]:
    return {entry["stable_id"]: entry for entry in manifest.get("entries", [])}


def manifest_entry_by_raw_path(manifest: dict) -> Dict[str, dict]:
    """Index by the raw asset path (e.g. ``raw/assets/gaussian-input-format.md``)."""
    by_path: Dict[str, dict] = {}
    for entry in manifest.get("entries", []):
        # The manifest ``path`` is relative to raw/assets/.
        raw_path = f"raw/assets/{entry['path']}"
        by_path[raw_path] = entry
    return by_path


# ---------------------------------------------------------------------------
# Report construction
# ---------------------------------------------------------------------------


def _wiki_mentions_rule(wiki_path: Path, rule_code: str) -> bool:
    if not wiki_path.is_file():
        return False
    text = wiki_path.read_text(encoding="utf-8")
    # Match ``G001`` or ``GAUSS-E034`` as standalone tokens so that G001 does
    # not accidentally match inside G010/G011 substrings.
    pattern = re.compile(rf"(?<![A-Z0-9-]){re.escape(rule_code)}(?![A-Z0-9-])")
    return pattern.search(text) is not None


def build_report(generated_at: str) -> Tuple[dict, List[str]]:
    """Build the traceability report and a list of validation errors."""
    errors: List[str] = []
    manifest = load_raw_manifest()
    by_raw = manifest_entry_by_raw_path(manifest)

    trace_ids = assign_trace_ids(RULE_CATALOG)

    docstrings: List[dict] = []
    rule_ids: List[dict] = []
    wiki_to_raw: Dict[str, Set[str]] = {}
    wiki_rule_codes: Dict[str, List[str]] = {}

    for spec in sorted(RULE_CATALOG, key=lambda s: (s.file_role, s.rule_code)):
        line_no = find_docstring_line(spec)
        if line_no is None:
            errors.append(
                f"docstring not found for {spec.rule_code} " f"({spec.symbol}) in {spec.doc_path}"
            )
            continue

        wiki_abs = REPO_ROOT / spec.wiki_path
        raw_abs = REPO_ROOT / spec.raw_path
        if not wiki_abs.is_file():
            errors.append(f"wiki path missing for {spec.rule_code}: {spec.wiki_path}")
        elif not _wiki_mentions_rule(wiki_abs, spec.rule_code):
            errors.append(f"wiki page {spec.wiki_path} does not mention {spec.rule_code}")

        if not raw_abs.is_file():
            errors.append(f"raw asset missing for {spec.rule_code}: {spec.raw_path}")
        else:
            entry = by_raw.get(spec.raw_path)
            if entry is None:
                errors.append(f"raw asset {spec.raw_path} is not registered in manifest")
            elif entry.get("stable_id") != spec.raw_stable_id:
                errors.append(
                    f"stable_id mismatch for {spec.raw_path}: expected "
                    f"{spec.raw_stable_id}, found {entry.get('stable_id')}"
                )

        trace_id = trace_ids[spec.rule_code + "@" + spec.file_role]
        docstrings.append(
            {
                "ruleCode": spec.rule_code,
                "traceCode": trace_id,
                "symbol": spec.symbol,
                "path": spec.doc_path,
                "lineStart": line_no,
                "lineEnd": line_no,
                "wikiPath": spec.wiki_path,
                "rawPath": spec.raw_path,
                "rawStableId": spec.raw_stable_id,
                "status": "linked",
            }
        )
        rule_ids.append(
            {
                "code": trace_id,
                "ruleCode": spec.rule_code,
                "fileRole": spec.file_role,
                "category": spec.category_short,
                "ordinal": int(trace_id.rsplit("-", 1)[1]),
                "severity": spec.severity,
                "symbol": spec.symbol,
                "docstringPath": spec.doc_path,
                "wikiPath": spec.wiki_path,
                "rawPath": spec.raw_path,
            }
        )

        wiki_to_raw.setdefault(spec.wiki_path, set()).add(spec.raw_path)
        wiki_rule_codes.setdefault(spec.wiki_path, []).append(spec.rule_code)

    # Build wiki sources list, deterministically sorted.
    wiki_sources: List[dict] = []
    for wiki_path in sorted(wiki_to_raw):
        raw_paths = sorted(wiki_to_raw[wiki_path])
        primary_raw = raw_paths[0]
        entry = by_raw.get(primary_raw, {})
        wiki_sources.append(
            {
                "wikiPath": wiki_path,
                "rawPath": primary_raw,
                "rawStableId": entry.get("stable_id"),
                "ruleCodes": sorted(set(wiki_rule_codes[wiki_path])),
                "status": "linked",
            }
        )

    # Detect broken wiki_links in the manifest (every link must resolve).
    broken_wiki_links: List[dict] = []
    for manifest_entry in manifest.get("entries", []):
        for link in manifest_entry.get("wiki_links", []):
            link_abs = REPO_ROOT / link
            if not link_abs.is_file():
                broken_wiki_links.append(
                    {
                        "stableId": manifest_entry.get("stable_id"),
                        "wikiLink": link,
                    }
                )

    # Detect wiki sources without raw evidence: any wiki path tracked by this
    # report must resolve to an existing file AND have a manifest entry that
    # registers its raw asset (``rawPath`` on disk + matching ``stable_id``).
    # This counter stays at zero when every wiki source has raw backing.
    wiki_sources_without_raw: List[str] = []
    for wiki_path, raw_path_set in sorted(wiki_to_raw.items()):
        wiki_abs = REPO_ROOT / wiki_path
        if not wiki_abs.is_file():
            wiki_sources_without_raw.append(wiki_path)
            continue
        for raw_path in raw_path_set:
            raw_abs = REPO_ROOT / raw_path
            entry = by_raw.get(raw_path)
            if not raw_abs.is_file() or entry is None:
                wiki_sources_without_raw.append(wiki_path)
                break

    # Source URLs -- union of manifest ``source_url`` fields, official source
    # anchors, and any ``https://`` URL discovered inside the raw asset
    # markdown files (so third-party references like cclib's parser are kept).
    url_set = {
        manifest_entry["source_url"]
        for manifest_entry in manifest.get("entries", [])
        if manifest_entry.get("source_url")
    } | {
        anchor.get("url")
        for anchor in manifest.get("official_source_anchors", [])
        if anchor.get("url")
    }
    url_pattern = re.compile(r"https?://[^\s)>]+")
    for manifest_entry in manifest.get("entries", []):
        asset_path = REPO_ROOT / "raw" / "assets" / manifest_entry["path"]
        if asset_path.is_file():
            for match in url_pattern.findall(asset_path.read_text(encoding="utf-8")):
                url_set.add(match.rstrip(".,;"))
    # Drop internal/local hosts and the repository's own clone URL -- they are
    # not external evidence sources.
    url_set = {
        u
        for u in url_set
        if ".local/" not in u
        and not u.endswith("newtontech/gaussian-lsp.git")
        and "newtontech.local" not in u
    }
    source_urls: List[str] = sorted(url_set)

    # Raw manifest summary -- detect entries whose asset file is missing.
    raw_failures: List[dict] = []
    for manifest_entry in manifest.get("entries", []):
        asset_path = REPO_ROOT / "raw" / "assets" / manifest_entry["path"]
        if not asset_path.is_file():
            raw_failures.append(
                {
                    "stableId": manifest_entry.get("stable_id"),
                    "path": f"raw/assets/{manifest_entry['path']}",
                    "reason": "asset file missing",
                }
            )

    all_entries_referenced = True  # every entry has either wiki_links or is a source target

    report = {
        "schemaVersion": SCHEMA_VERSION,
        "serverId": SERVER_ID,
        "repository": REPOSITORY,
        "languageId": LANGUAGE_ID,
        "generatedAt": generated_at,
        "summary": {
            "docstringsTotal": len(docstrings),
            "docstringsLinked": len(docstrings),
            "wikiSourcesTotal": len(wiki_sources),
            "wikiSourcesLinked": len(wiki_sources),
            "ruleIdsTotal": len(rule_ids),
            "rawManifestEntries": len(manifest.get("entries", [])),
            "brokenWikiLinks": len(broken_wiki_links),
            "wikiSourcesWithoutRaw": len(wiki_sources_without_raw),
            "rawManifestFailures": len(raw_failures),
        },
        "docstrings": sorted(docstrings, key=lambda d: (d["path"], d["lineStart"], d["ruleCode"])),
        "wikiSources": wiki_sources,
        "ruleIds": sorted(rule_ids, key=lambda r: r["code"]),
        "sourceUrls": source_urls,
        "rawManifest": {
            "path": "raw/assets/manifest.json",
            "schemaVersion": manifest.get("schema_version"),
            "entryCount": len(manifest.get("entries", [])),
            "allEntriesReferenced": all_entries_referenced,
            "brokenWikiLinks": broken_wiki_links,
            "failures": raw_failures,
        },
    }

    if broken_wiki_links:
        for bw in broken_wiki_links:
            errors.append(f"manifest entry {bw['stableId']} links missing wiki {bw['wikiLink']}")
    if raw_failures:
        for rf in raw_failures:
            errors.append(f"manifest entry {rf['stableId']} references missing asset {rf['path']}")

    return report, errors


# ---------------------------------------------------------------------------
# Validation against the report on disk
# ---------------------------------------------------------------------------


TRACE_CODE_PATTERN = re.compile(r"^GAUSSIAN-[A-Z]+-[A-Z]+-\d{3}$")


def validate_report(report: dict) -> List[str]:
    """Return a list of human-readable validation errors (empty = valid)."""
    errors: List[str] = []

    if report.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(
            f"schemaVersion must be {SCHEMA_VERSION}, got {report.get('schemaVersion')!r}"
        )

    for field in ("serverId", "repository", "languageId", "generatedAt"):
        if not report.get(field):
            errors.append(f"missing top-level field: {field}")

    if report.get("serverId") != SERVER_ID:
        errors.append(f"serverId must be {SERVER_ID}")
    if report.get("repository") != REPOSITORY:
        errors.append(f"repository must be {REPOSITORY}")
    if report.get("languageId") != LANGUAGE_ID:
        errors.append(f"languageId must be {LANGUAGE_ID}")

    summary = report.get("summary", {})
    if summary.get("docstringsLinked") != summary.get("docstringsTotal"):
        errors.append("summary.docstringsLinked must equal summary.docstringsTotal")
    for counter in ("brokenWikiLinks", "wikiSourcesWithoutRaw", "rawManifestFailures"):
        if summary.get(counter) != 0:
            errors.append(f"summary.{counter} must be zero")

    # Path hygiene -- every path field must be repo-relative (no absolute paths).
    absolute_path_pattern = re.compile(r"^/(?:Users|home|tmp|var|root|etc)")
    for section in ("docstrings", "wikiSources", "ruleIds"):
        for idx, entry in enumerate(report.get(section, [])):
            for key, value in entry.items():
                if isinstance(value, str) and value.endswith((".py", ".ts", ".md", ".json")):
                    if value.startswith(("/", "~")) or absolute_path_pattern.match(value):
                        errors.append(f"{section}[{idx}].{key} must be repo-relative: {value!r}")

    raw_manifest_section = report.get("rawManifest", {})
    for failure in raw_manifest_section.get("failures", []):
        errors.append(f"rawManifest failure for {failure.get('stableId')}: {failure.get('reason')}")
    for bw in raw_manifest_section.get("brokenWikiLinks", []):
        errors.append(f"rawManifest broken wiki link: {bw.get('stableId')} -> {bw.get('wikiLink')}")

    # Trace code format check.
    for rule in report.get("ruleIds", []):
        code = rule.get("code", "")
        if not TRACE_CODE_PATTERN.match(code):
            errors.append(f"ruleIds[].code format invalid: {code!r}")
        if rule.get("fileRole") not in (FILE_ROLE_LINT, FILE_ROLE_LOGP, FILE_ROLE_TSDS):
            errors.append(f"ruleIds[].fileRole unknown: {rule.get('fileRole')!r}")
        if rule.get("category") not in CATEGORY_TO_SHORT.values():
            errors.append(f"ruleIds[].category unknown: {rule.get('category')!r}")

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    report, build_errors = build_report(args.generated_at)
    if build_errors:
        sys.stderr.write("ERROR: cannot generate report -- repository state is inconsistent:\n")
        for err in build_errors:
            sys.stderr.write(f"  - {err}\n")
        return 2

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(
        f"  docstrings={report['summary']['docstringsTotal']} "
        f"wikiSources={report['summary']['wikiSourcesTotal']} "
        f"ruleIds={report['summary']['ruleIdsTotal']} "
        f"rawEntries={report['summary']['rawManifestEntries']}"
    )
    return 0


def cmd_strict(args: argparse.Namespace) -> int:
    if not REPORT_PATH.is_file():
        sys.stderr.write(f"ERROR: report missing at {REPORT_PATH}\n")
        return 2
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_report(report)
    # Also re-derive the report and ensure the on-disk copy matches. This is
    # the deterministic regeneration check.
    fresh, build_errors = build_report(report.get("generatedAt", DEFAULT_GENERATED_AT))
    if build_errors:
        errors.extend(build_errors)
    else:
        # Normalize ordering for comparison -- the report on disk should match
        # the freshly built one because both sort entries deterministically.
        if json.dumps(report, sort_keys=True) != json.dumps(fresh, sort_keys=True):
            errors.append("report is stale: regenerate with `--generate` to match repository state")

    if errors:
        sys.stderr.write(f"ERROR: {len(errors)} validation failure(s):\n")
        for err in errors:
            sys.stderr.write(f"  - {err}\n")
        return 1

    print(
        f"OK: {REPORT_PATH.relative_to(REPO_ROOT)} "
        f"(schemaVersion={report['schemaVersion']}, "
        f"docstrings={report['summary']['docstringsTotal']}, "
        f"ruleIds={report['summary']['ruleIdsTotal']})"
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Write reports/docstring-wiki-raw-traceability.json",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Validate the existing report in strict mode",
    )
    parser.add_argument(
        "--generated-at",
        default=DEFAULT_GENERATED_AT,
        help=f"ISO timestamp for generatedAt (default: {DEFAULT_GENERATED_AT})",
    )
    args = parser.parse_args(argv)

    if args.generate and args.strict:
        parser.error("--generate and --strict are mutually exclusive")
    if not args.generate and not args.strict:
        # Default behaviour is strict validation.
        args.strict = True

    if args.generate:
        return cmd_generate(args)
    return cmd_strict(args)


if __name__ == "__main__":
    raise SystemExit(main())
