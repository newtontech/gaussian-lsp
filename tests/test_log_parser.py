"""Unit tests for the Gaussian runtime log parser (DiagnosticEnvelope/v1).

Covers issue #87 backend-only vertical slice: Python parity with the
TypeScript ``parseLog`` surface, extended with the four production failure
modes fleet consumers care about (SCF, geometry/Link, optimization
exhaustion, memory/disk exhaustion) plus explicit refusal reasons for the
``fix`` operation on unsafe cases.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaussian_lsp import tool
from gaussian_lsp.log_parser import (
    ALL_LOG_CODES,
    CODE_ERROR_TERMINATION,
    CODE_GEOMETRY_PARSE_FAILURE,
    CODE_LINK_FAULT,
    CODE_MEMORY_EXHAUSTED,
    CODE_OPT_NOT_CONVERGED,
    CODE_OPT_STEP_UNCONVERGED,
    CODE_SCF_NOT_CONVERGED,
    LINK_KNOWLEDGE,
    LogFinding,
    is_gaussian_log,
    log_manifest,
    parse_log,
)

FIXTURES = Path(__file__).parent / "fixtures" / "log"
RULES = Path(__file__).parent / "fixtures" / "rules"

# Envelope fields the issue acceptance criteria require on log findings.
REQUIRED_FINDING_FIELDS = {
    "diagnostic_envelope",
    "diagnostic_engine",
    "code",
    "severity",
    "category",
    "confidence",
    "source",
    "range",
    "software",
    "file_type",
    "path",
    "blocking",
    "fix_hints",
    "message",
}


# ---------------------------------------------------------------------------
# parse_log(): unit behavior
# ---------------------------------------------------------------------------


def _codes(findings: list[dict]) -> set[str]:
    return {item["code"] for item in findings}


def test_parse_log_empty_returns_truncation_information() -> None:
    findings = parse_log("")
    assert len(findings) == 1
    assert findings[0]["severity"] == "information"
    assert findings[0]["blocking"] is False


def test_parse_log_scf_convergence_failure_carries_last_scf_done_facts() -> None:
    text = (
        " SCF Done:  E(RHF) = -74.96 A.U. after  50 cycles\n"
        " Convergence failure -- SCF cycle limit reached.\n"
    )
    findings = parse_log(text, path="t.log")
    by_code = {f["code"]: f for f in findings}
    assert CODE_SCF_NOT_CONVERGED in by_code
    item = by_code[CODE_SCF_NOT_CONVERGED]
    assert item["severity"] == "error"
    assert item["blocking"] is True
    assert item["facts"]["last_method"] == "RHF"
    assert item["facts"]["last_cycles"] == 50
    assert item["facts"]["last_energy"] == pytest.approx(-74.96)


def test_parse_log_scf_convergence_failure_without_scf_done_line_still_emits() -> None:
    text = " Convergence failure in SCF.\n"
    findings = parse_log(text)
    assert CODE_SCF_NOT_CONVERGED in _codes(findings)


def test_parse_log_scf_fails_to_conquer_variant_emits() -> None:
    text = " SCF fails to converge after 100 cycles.\n"
    findings = parse_log(text)
    assert CODE_SCF_NOT_CONVERGED in _codes(findings)


def test_parse_log_geometry_error_emits_e035() -> None:
    text = " Reading geometry.\n Error in geometry specification.\n"
    findings = parse_log(text)
    assert CODE_GEOMETRY_PARSE_FAILURE in _codes(findings)
    item = next(f for f in findings if f["code"] == CODE_GEOMETRY_PARSE_FAILURE)
    assert item["category"] == "syntax"


def test_parse_log_geometry_input_error_variant_emits() -> None:
    text = " Input Error: invalid basis set specification.\n"
    findings = parse_log(text)
    assert CODE_GEOMETRY_PARSE_FAILURE in _codes(findings)


def test_parse_log_supervisor_error_termination_emits_e036_and_e037() -> None:
    text = " Error termination via Lnk1e in /scr1/g16/l502.exe at " "Tue Mar 10 15:05:09 2020.\n"
    findings = parse_log(text)
    codes = _codes(findings)
    assert CODE_ERROR_TERMINATION in codes
    assert CODE_LINK_FAULT in codes
    link_finding = next(f for f in findings if f["code"] == CODE_LINK_FAULT)
    assert link_finding["facts"]["link_number"] == 502
    assert link_finding["facts"]["link_role"] == "SCF iteration"
    assert "l502" in link_finding["facts"]["link_executable"]
    et_finding = next(f for f in findings if f["code"] == CODE_ERROR_TERMINATION)
    assert et_finding["facts"]["supervisor"] == "Lnk1e"
    assert et_finding["facts"]["link_number"] == 502


def test_parse_log_abbreviated_error_termination_form_emits() -> None:
    """Existing minimal fixtures use 'Error termination via L301.' form.

    The parser must accept both the canonical supervisor form and the
    abbreviated form so legacy fixtures keep emitting structured findings.
    """
    text = " Error termination via L301.\n"
    findings = parse_log(text)
    codes = _codes(findings)
    assert CODE_ERROR_TERMINATION in codes
    assert CODE_LINK_FAULT in codes
    link_finding = next(f for f in findings if f["code"] == CODE_LINK_FAULT)
    assert link_finding["facts"]["link_number"] == 301
    assert link_finding["facts"]["link_role"] == "basis set specification"


def test_parse_log_optimization_stopped_emits_e038() -> None:
    text = " Optimization stopped.\n  -- Number of steps exceeded, NStep=  50.\n"
    findings = parse_log(text)
    assert CODE_OPT_NOT_CONVERGED in _codes(findings)
    item = next(f for f in findings if f["code"] == CODE_OPT_NOT_CONVERGED)
    assert item["facts"]["nstep"] == 50
    assert item["artifact_roles"][-1] == "optimization"


def test_parse_log_optimization_stopped_without_nstep_still_emits() -> None:
    text = " Optimization stopped.\n"
    findings = parse_log(text)
    assert CODE_OPT_NOT_CONVERGED in _codes(findings)


def test_parse_log_memory_exhausted_emits_e039() -> None:
    text = (
        " Not enough memory to allocate work array 1 of length 12345678.\n"
        " Wanted    4096000000 bytes of mem, got   536870912 bytes.\n"
    )
    findings = parse_log(text)
    assert CODE_MEMORY_EXHAUSTED in _codes(findings)
    item = next(f for f in findings if f["code"] == CODE_MEMORY_EXHAUSTED)
    assert "link0" in item["artifact_roles"]


def test_parse_log_item_no_emits_non_blocking_warning() -> None:
    """``Item ... NO`` mid-optimization is a warning, not an error.

    Real Gaussian logs emit dozens of these during a long optimization; only
    surface them as warning-level findings so the fleet probe does not gate
    on per-step convergence lines.
    """
    text = (
        " Item               Value     Threshold  Converged?\n"
        " Maximum Force       0.000144   0.000450   NO\n"
    )
    findings = parse_log(text)
    item = next(
        (f for f in findings if f["code"] == CODE_OPT_STEP_UNCONVERGED),
        None,
    )
    assert item is not None
    assert item["severity"] == "warning"
    assert item["blocking"] is False


def test_parse_log_normal_termination_returns_no_findings() -> None:
    text = (
        " SCF Done:  E(RHF) = -74.96 A.U. after  5 cycles\n"
        " Normal termination of Gaussian 16 at Tue Mar 10 15:05:09 2020.\n"
    )
    findings = parse_log(text)
    # No Error termination, no SCF failure, no opt failure -- clean.
    for code in (
        CODE_SCF_NOT_CONVERGED,
        CODE_ERROR_TERMINATION,
        CODE_LINK_FAULT,
        CODE_OPT_NOT_CONVERGED,
        CODE_MEMORY_EXHAUSTED,
    ):
        assert code not in _codes(findings)


def test_parse_log_finding_shape_matches_v1_envelope() -> None:
    text = " Convergence failure -- SCF cycle limit reached.\n"
    findings = parse_log(text, path="x.log")
    assert findings, "expected at least one finding"
    item = findings[0]
    assert REQUIRED_FINDING_FIELDS <= set(
        item
    ), f"missing fields: {REQUIRED_FINDING_FIELDS - set(item)}"
    assert item["diagnostic_envelope"] == "v1"
    assert item["diagnostic_engine"] == "1.0"
    assert item["software"] == "gaussian"
    assert item["file_type"] == "log"
    assert item["path"] == "x.log"
    assert "actions" in item
    assert "source_provenance" in item
    assert "facts" in item


def test_parse_log_blocking_findings_carry_refusal_reason() -> None:
    """The fix surface must explain *why* a quickfix is unsafe to auto-apply."""
    text = " Error termination via Lnk1e in /scr1/g16/l502.exe at " "Tue Mar 10 15:05:09 2020.\n"
    findings = parse_log(text, path="y.log")
    blocking = [f for f in findings if f["blocking"]]
    assert blocking
    for item in blocking:
        assert item.get(
            "refusal_reason"
        ), f"{item['code']}: blocking finding missing refusal_reason"
        for action in item.get("actions", []):
            assert "safe_to_auto_apply" in action
            assert action["safe_to_auto_apply"] is False
            assert action.get("refusal_reason"), f"{item['code']}: action missing refusal_reason"


def test_parse_log_link_fault_carries_knowledge_from_link_table() -> None:
    text = " Error termination via Lnk1e in /scr1/g16/l9999.exe at " "Tue Mar 10 15:11:35 2020.\n"
    findings = parse_log(text)
    item = next(f for f in findings if f["code"] == CODE_LINK_FAULT)
    assert item["facts"]["link_role"] == "termination / archive"
    # The link knowledge table must populate fix_hints.
    assert any("MaxCycle" in hint for hint in item["fix_hints"])


def test_parse_log_unknown_link_number_synthesizes_role() -> None:
    text = " Error termination via Lnk1e in /scr1/g16/l666.exe at " "Tue Mar 10 15:11:35 2020.\n"
    findings = parse_log(text)
    item = next(f for f in findings if f["code"] == CODE_LINK_FAULT)
    # l666 is not in the knowledge table -> synthesizes a generic role.
    assert item["facts"]["link_number"] == 666
    assert item["facts"]["link_role"] == "unknown"


def test_parse_log_deterministic_order() -> None:
    """Same input always produces the same ordering."""
    text = (
        " Item Value Threshold NO\n"
        " Convergence failure.\n"
        " Error termination via Lnk1e in /scr1/g16/l502.exe.\n"
    )
    a = parse_log(text)
    b = parse_log(text)
    assert [item["code"] for item in a] == [item["code"] for item in b]


def test_parse_log_blocking_findings_sort_first() -> None:
    text = " Item Value Threshold NO\n" " Optimization stopped.\n"
    findings = parse_log(text)
    blocking_idx = [i for i, item in enumerate(findings) if item["blocking"]]
    nonblocking_idx = [i for i, item in enumerate(findings) if not item["blocking"]]
    if blocking_idx and nonblocking_idx:
        assert max(blocking_idx) < min(nonblocking_idx)


# ---------------------------------------------------------------------------
# Fixture-based regression: real Gaussian-shaped logs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture, must_include, must_be_ok",
    [
        ("scf_converged.out", set(), True),
        ("normal_termination.out", set(), True),
        ("scf_not_converged.out", {CODE_SCF_NOT_CONVERGED}, False),
        (
            "error_termination_l502.log",
            {CODE_SCF_NOT_CONVERGED, CODE_ERROR_TERMINATION, CODE_LINK_FAULT},
            False,
        ),
        (
            "error_termination_l301.log",
            {CODE_ERROR_TERMINATION, CODE_LINK_FAULT},
            False,
        ),
        (
            "optimization_not_converged.log",
            {CODE_OPT_NOT_CONVERGED, CODE_OPT_STEP_UNCONVERGED},
            False,
        ),
        (
            "memory_exhausted.log",
            {CODE_MEMORY_EXHAUSTED, CODE_ERROR_TERMINATION},
            False,
        ),
        (
            "geometry_parse_failure.log",
            {CODE_GEOMETRY_PARSE_FAILURE, CODE_ERROR_TERMINATION},
            False,
        ),
    ],
)
def test_log_fixture_expectations(
    fixture: str,
    must_include: set[str],
    must_be_ok: bool,
) -> None:
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    findings = parse_log(text, path=str(FIXTURES / fixture))
    codes = _codes(findings)
    assert must_include <= codes, f"{fixture}: expected {must_include}, got {sorted(codes)}"
    blocking = any(f["blocking"] for f in findings)
    assert blocking != must_be_ok


def test_existing_scf_converged_fixture_emits_no_blocking() -> None:
    text = (FIXTURES / "scf_converged.out").read_text(encoding="utf-8")
    findings = parse_log(text)
    assert not any(f["blocking"] for f in findings)


# ---------------------------------------------------------------------------
# LogFinding dataclass -> dict round-trip
# ---------------------------------------------------------------------------


def test_log_finding_to_dict_includes_all_envelope_fields() -> None:
    finding = LogFinding(
        code=CODE_SCF_NOT_CONVERGED,
        severity="error",
        message="test",
        line=10,
        facts={"k": "v"},
        fix_hints=("hint1", "hint2"),
        actions=({"kind": "x", "safe_to_auto_apply": False},),
        source_provenance={"rule": CODE_SCF_NOT_CONVERGED, "source": "test"},
        manual_ref="https://example.com/",
        refusal_reason="unsafe",
    )
    payload = finding.to_dict(path="/tmp/x.log")
    assert payload["code"] == CODE_SCF_NOT_CONVERGED
    assert payload["severity"] == "error"
    assert payload["blocking"] is True  # default
    assert payload["range"]["start"]["line"] == 9  # 0-based
    assert payload["facts"] == {"k": "v"}
    assert payload["fix_hints"] == ["hint1", "hint2"]
    assert payload["actions"] == [{"kind": "x", "safe_to_auto_apply": False}]
    assert payload["refusal_reason"] == "unsafe"
    assert payload["manual_ref"] == "https://example.com/"
    assert payload["path"] == "/tmp/x.log"


# ---------------------------------------------------------------------------
# is_gaussian_log / detection
# ---------------------------------------------------------------------------


def test_is_gaussian_log_accepts_log_with_markers(tmp_path: Path) -> None:
    p = tmp_path / "x.log"
    p.write_text(
        "Entering Gaussian System\nNormal termination\n",
        encoding="utf-8",
    )
    assert is_gaussian_log(p) is True


def test_is_gaussian_log_rejects_wrong_extension(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("Normal termination\n", encoding="utf-8")
    assert is_gaussian_log(p) is False


def test_is_gaussian_log_rejects_log_without_markers(tmp_path: Path) -> None:
    p = tmp_path / "x.out"
    p.write_text("just a server log\n", encoding="utf-8")
    assert is_gaussian_log(p) is False


# ---------------------------------------------------------------------------
# log_manifest(): parent probe contract
# ---------------------------------------------------------------------------


def test_log_manifest_lists_all_codes() -> None:
    manifest = log_manifest()
    assert manifest["software"] == "gaussian"
    assert manifest["log_envelope"] == "DiagnosticEnvelope/v1"
    assert manifest["capability"] == "runtime-log"
    assert manifest["status"] == "available"
    assert set(manifest["codes"]) == set(ALL_LOG_CODES)
    for code, body in manifest["codes"].items():
        assert body["capability"] == "runtime-log"
        assert body["severity"] in {"error", "warning", "information", "hint"}
        assert "summary" in body
    # Every well-known Link in the knowledge table is mirrored into the
    # manifest so the parent probe can branch on link role.
    assert "502" in manifest["link_map"]
    assert manifest["link_map"]["502"]["role"] == "SCF iteration"


# ---------------------------------------------------------------------------
# LINK_KNOWLEDGE table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("link_num", sorted(LINK_KNOWLEDGE))
def test_link_knowledge_table_entries_have_required_fields(link_num: int) -> None:
    entry = LINK_KNOWLEDGE[link_num]
    assert "role" in entry
    assert "cause" in entry
    assert "hint" in entry
    assert entry["role"], f"l{link_num}: empty role"
    assert entry["cause"], f"l{link_num}: empty cause"
    assert entry["hint"], f"l{link_num}: empty hint"


# ---------------------------------------------------------------------------
# Tool CLI: parse-log operation
# ---------------------------------------------------------------------------


class TestParseLogCLI:
    def test_parse_log_subcommand_returns_v1_envelope(self, capsys) -> None:
        rc = tool.main(["parse-log", str(FIXTURES / "scf_not_converged.out")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["operation"] == "parse-log"
        assert payload["diagnostic_envelope"] == "v1"
        assert payload["software"] == "gaussian"
        assert payload["ok"] is False
        assert CODE_SCF_NOT_CONVERGED in _codes(payload["diagnostics"])
        # The log capability manifest is inlined so consumers do not need a
        # second CLI call to discover the rule surface.
        assert "log_manifest" in payload
        assert payload["log_manifest"]["capability"] == "runtime-log"

    def test_parse_log_fail_on_blocking_exits_nonzero(self) -> None:
        rc = tool.main(
            [
                "parse-log",
                str(FIXTURES / "scf_not_converged.out"),
                "--fail-on-blocking",
            ]
        )
        assert rc == 1

    def test_parse_log_fail_on_blocking_exits_zero_for_clean(self, capsys) -> None:
        rc = tool.main(
            [
                "parse-log",
                str(FIXTURES / "normal_termination.out"),
                "--fail-on-blocking",
            ]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["diagnostics"] == []

    def test_parse_log_error_termination_fixture_emits_three_blocking(self, capsys) -> None:
        rc = tool.main(["parse-log", str(FIXTURES / "error_termination_l502.log")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        codes = _codes(payload["diagnostics"])
        assert {
            CODE_SCF_NOT_CONVERGED,
            CODE_ERROR_TERMINATION,
            CODE_LINK_FAULT,
        } <= codes
        assert payload["summary"]["blocking"] >= 3
        assert payload["summary"]["errors"] >= 3

    def test_parse_log_optimization_fixture_emits_e038_and_w034(self, capsys) -> None:
        rc = tool.main(["parse-log", str(FIXTURES / "optimization_not_converged.log")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        codes = _codes(payload["diagnostics"])
        assert CODE_OPT_NOT_CONVERGED in codes
        assert CODE_OPT_STEP_UNCONVERGED in codes
        # The warning is non-blocking.
        w034 = next(d for d in payload["diagnostics"] if d["code"] == CODE_OPT_STEP_UNCONVERGED)
        assert w034["blocking"] is False

    def test_parse_log_memory_exhausted_fixture_emits_e039(self, capsys) -> None:
        rc = tool.main(["parse-log", str(FIXTURES / "memory_exhausted.log")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        codes = _codes(payload["diagnostics"])
        assert CODE_MEMORY_EXHAUSTED in codes
        item = next(d for d in payload["diagnostics"] if d["code"] == CODE_MEMORY_EXHAUSTED)
        assert item["artifact_roles"][-1] == "link0"


class TestCheckOnLogRoutesThroughParser:
    """``check`` auto-detects a Gaussian log and routes through parse_log_path."""

    def test_check_on_log_file_returns_parse_log_operation(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "scf_not_converged.out")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        # check on a log file routes through parse_log_path -> operation=check
        # but the payload shape matches parse-log (file_type='out' on the
        # individual diagnostics per the v1 contract).
        assert payload["operation"] == "check"
        assert payload["ok"] is False
        assert payload["diagnostics"], "expected diagnostics from parse_log"
        assert payload["diagnostics"][0]["file_type"] == "out"
        assert CODE_SCF_NOT_CONVERGED in _codes(payload["diagnostics"])
        assert "log_manifest" in payload

    def test_check_on_log_with_fail_on_blocking_exits_nonzero(self) -> None:
        rc = tool.main(
            [
                "check",
                str(FIXTURES / "error_termination_l301.log"),
                "--fail-on-blocking",
            ]
        )
        assert rc == 1

    def test_check_on_log_clean_returns_ok(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "normal_termination.out")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["diagnostics"] == []


class TestFixOnLogFindings:
    """The fix operation surfaces refusal_reason for unsafe runtime fixes."""

    def test_fix_returns_actions_with_refusal_reason(self, capsys) -> None:
        # Use a fixture file with a known SCF failure; fix operates on the
        # whole-file diagnostics when no --line/--character is given.
        rc = tool.main(["fix", str(FIXTURES / "error_termination_l502.log")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        actions = payload["actions"]
        assert actions, "expected at least one fix action for runtime finding"
        # Every action must declare safe_to_auto_apply=False AND a
        # refusal_reason explaining why auto-apply is unsafe.
        for action in actions:
            assert action["safe_to_auto_apply"] is False
            assert action.get("refusal_reason"), f"action missing refusal_reason: {action}"

    def test_fix_on_clean_log_returns_empty_actions(self, capsys) -> None:
        rc = tool.main(["fix", str(FIXTURES / "normal_termination.out")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["actions"] == []

    def test_fix_actions_include_first_party_action_kind(self, capsys) -> None:
        rc = tool.main(["fix", str(FIXTURES / "memory_exhausted.log")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        actions = payload["actions"]
        # The log parser emits first-party actions with action_kind data.
        kinds = {a["data"].get("action_kind") for a in actions}
        assert kinds, "expected first-party action kinds in fix payload"


# ---------------------------------------------------------------------------
# Rule catalog fixtures
# ---------------------------------------------------------------------------


class TestRuleCatalogFixtures:
    @pytest.mark.parametrize(
        "rule_file",
        sorted(RULES.glob("log_*.json")),
    )
    def test_log_rule_fixture_documents_expected_codes(self, rule_file: Path) -> None:
        spec = json.loads(rule_file.read_text(encoding="utf-8"))
        assert "rule" in spec
        assert "code" in spec
        assert "expected" in spec
        assert spec["expected"]["code"] == spec["code"]
        assert spec["code"] in ALL_LOG_CODES

    @pytest.mark.parametrize(
        "rule_file",
        sorted(RULES.glob("log_*.json")),
    )
    def test_log_rule_fixture_input_triggers_expected_code(self, rule_file: Path) -> None:
        spec = json.loads(rule_file.read_text(encoding="utf-8"))
        findings = parse_log(spec["input"])
        codes = _codes(findings)
        assert spec["code"] in codes, (
            f"{rule_file.name}: input did not trigger {spec['code']} " f"(got {sorted(codes)})"
        )


# ---------------------------------------------------------------------------
# Closed-loop: openqc smoke / parent probe contract
# ---------------------------------------------------------------------------


def test_log_manifest_is_json_serializable_for_fleet_probe() -> None:
    payload = log_manifest()
    serialized = json.dumps(payload, sort_keys=True)
    assert "GAUSS-E034" in serialized
    assert "runtime-log" in serialized


def test_parse_log_inlines_manifest_for_parse_log_cli(capsys) -> None:
    rc = tool.main(["parse-log", str(FIXTURES / "normal_termination.out")])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["log_manifest"]["codes"]
    # The manifest must agree with parse_log()'s emitted codes so the parent
    # probe can branch on parse-log output without false positives.
    assert set(payload["log_manifest"]["codes"]) >= {
        item["code"] for item in payload["diagnostics"]
    }
