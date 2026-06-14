from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaussian_lsp import tool
from gaussian_lsp.parser.gjf_parser import GJFParser
from gaussian_lsp.preflight import (
    ALL_ROLES,
    CODE_DFT_WITHOUT_FUNCTIONAL,
    CODE_GUESS_READ_WITHOUT_OLDCHK,
    CODE_LOW_MEM,
    CODE_METHOD_BASIS_MISMATCH,
    CODE_MISSING_BASIS,
    CODE_MISSING_ROUTE,
    CODE_OPT_MAXCYCLE_DISABLED,
    CODE_PSEUDO_WITHOUT_BASIS,
    CODE_STRUCTURE_EMPTY,
    CODE_VERSION_ASSUMPTION,
    DEFAULT_MEM_WARNING_MB,
    ArtifactGraph,
    _detect_dft_functional,
    _extract_route_int,
    _parse_mem_mb,
    build_artifact_graph,
    fleet_manifest,
    looks_like_gaussian_workspace,
    preflight_diagnostics,
    resolve_version_assumption,
)
from gaussian_lsp.tool import (
    _dedupe_preflight,
    _looks_like_workspace,
    manifest_path,
    preflight_path,
)

FIXTURES = Path(__file__).parent / "fixtures" / "preflight"

# Envelope fields the issue acceptance criteria require on failing fixtures.
REQUIRED_FAILING_FIELDS = {
    "code",
    "severity",
    "path",
    "range",
    "blocking",
    "category",
    "source_provenance",
}


def _envelope_codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"]}


def _parse(text: str):
    return GJFParser().parse(text)


# --- Envelope shape --------------------------------------------------------


def test_agent_check_payload_carries_diagnostic_envelope_v1(capsys) -> None:
    # No --fail-on-blocking, so the CLI exits 0 even with blocking findings;
    # the contract here is the envelope shape, not the exit code.
    rc = tool.main(["check", str(FIXTURES / "missing_route" / "input.gjf")])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["diagnostic_envelope"] == "v1"
    assert payload["diagnostic_engine"] == "1.0"
    assert payload["software"] == "gaussian"
    assert payload["capabilities"]["operation"] == "check"
    assert "version_assumption" in payload
    assert payload["version_assumption"]["software"] == "gaussian"
    assert isinstance(payload.get("artifacts"), list)
    assert payload["artifacts"]
    # preflight GAUSSIAN601 (missing route) is merged into the check payload.
    assert CODE_MISSING_ROUTE in _envelope_codes(payload)


def test_failing_diagnostics_carry_required_envelope_fields() -> None:
    payload = preflight_path(FIXTURES / "missing_route" / "input.gjf")
    failing = [item for item in payload["diagnostics"] if item["code"] == CODE_MISSING_ROUTE]
    assert failing, "missing_route fixture must emit GAUSSIAN601"
    item = failing[0]
    for field in REQUIRED_FAILING_FIELDS:
        assert field in item, f"missing required envelope field: {field}"
    assert item["confidence"] >= 0.0
    assert "actions" in item and item["actions"]
    assert "fix_hints" in item and item["fix_hints"]
    assert "facts" in item
    assert "artifact_roles" in item
    assert item["range"]["start"]["line"] >= 0
    assert "character" in item["range"]["start"]


# --- Fixture behavior ------------------------------------------------------


@pytest.mark.parametrize(
    "fixture, expected_ok, must_include",
    [
        ("valid_scf", True, set()),
        ("missing_route", False, {CODE_MISSING_ROUTE}),
        ("missing_basis", False, {CODE_MISSING_BASIS}),
        ("guess_read_no_oldchk", False, {CODE_GUESS_READ_WITHOUT_OLDCHK}),
        ("low_mem", True, {CODE_LOW_MEM}),
        ("method_basis_mismatch", False, {CODE_METHOD_BASIS_MISMATCH}),
    ],
)
def test_preflight_fixture_expectations(
    fixture: str,
    expected_ok: bool,
    must_include: set[str],
) -> None:
    payload = preflight_path(FIXTURES / fixture / "input.gjf")
    codes = _envelope_codes(payload)
    assert (
        payload["ok"] is expected_ok
    ), f"{fixture}: expected ok={expected_ok}, got codes={sorted(codes)}"
    assert must_include <= codes, f"{fixture}: expected codes {must_include}, got {sorted(codes)}"


def test_valid_scf_fixture_has_no_blocking_or_error_diagnostics() -> None:
    payload = preflight_path(FIXTURES / "valid_scf" / "input.gjf")
    assert payload["summary"]["errors"] == 0
    assert payload["summary"]["blocking"] == 0
    error_codes = {
        CODE_MISSING_ROUTE,
        CODE_STRUCTURE_EMPTY,
        CODE_MISSING_BASIS,
        CODE_GUESS_READ_WITHOUT_OLDCHK,
        CODE_METHOD_BASIS_MISMATCH,
        CODE_DFT_WITHOUT_FUNCTIONAL,
    }
    assert not (_envelope_codes(payload) & error_codes)


def test_low_mem_is_non_blocking_warning_with_threshold_fact() -> None:
    payload = preflight_path(FIXTURES / "low_mem" / "input.gjf")
    item = next(d for d in payload["diagnostics"] if d["code"] == CODE_LOW_MEM)
    assert item["severity"] == "warning"
    assert item["blocking"] is False
    assert item["facts"]["mem_mb"] == 100.0
    assert item["facts"]["threshold_mb"] == DEFAULT_MEM_WARNING_MB


def test_low_mem_intent_override_changes_threshold(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    # %mem=100MB is below the default 256 MB threshold -> warning fires.
    (case / "input.gjf").write_text(
        "%mem=100MB\n"
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    base = preflight_path(case / "input.gjf")
    assert CODE_LOW_MEM in _envelope_codes(base)

    cfg = case / ".gaussian-lsp"
    cfg.mkdir()
    # Override the threshold down to 50 MB so %mem=100MB is no longer below it.
    (cfg / "intent.json").write_text(json.dumps({"mem_warning_mb": 50}), encoding="utf-8")
    overridden = preflight_path(case / "input.gjf")
    assert CODE_LOW_MEM not in _envelope_codes(overridden)


# --- version-aware-keywords ------------------------------------------------


def test_version_assumption_unknown_when_intent_absent() -> None:
    assumption = resolve_version_assumption(None)
    assert assumption["exact_runtime_known"] is False
    assert assumption["declared_by"] == "fallback"
    assert assumption["software_version"] == "unknown"


def test_version_assumption_known_when_intent_declares_version() -> None:
    assumption = resolve_version_assumption(
        {"software_version": "gaussian >=g16", "runtime_image": "img:g16"}
    )
    assert assumption["exact_runtime_known"] is True
    assert assumption["declared_by"] == "intent"
    assert assumption["software_version"] == "gaussian >=g16"


def test_version_assumption_information_diagnostic_when_unknown(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "input.gjf").write_text(
        "%mem=1GB\n"
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    payload = preflight_path(case / "input.gjf")
    item = next(
        (d for d in payload["diagnostics"] if d["code"] == CODE_VERSION_ASSUMPTION),
        None,
    )
    assert item is not None
    assert item["severity"] == "information"
    assert item["blocking"] is False
    assert item["version_assumption"]["exact_runtime_known"] is False


def test_version_assumption_silent_when_intent_declares_version(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "input.gjf").write_text(
        "%mem=1GB\n"
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    cfg = case / ".gaussian-lsp"
    cfg.mkdir()
    (cfg / "intent.json").write_text(
        json.dumps({"software_version": "gaussian >=g16"}), encoding="utf-8"
    )
    payload = preflight_path(case / "input.gjf")
    assert CODE_VERSION_ASSUMPTION not in _envelope_codes(payload)
    assert payload["version_assumption"]["exact_runtime_known"] is True


def test_method_basis_mismatch_carries_version_assumption() -> None:
    payload = preflight_path(FIXTURES / "method_basis_mismatch" / "input.gjf")
    item = next(d for d in payload["diagnostics"] if d["code"] == CODE_METHOD_BASIS_MISMATCH)
    assert item["facts"]["basis"] == "STO-3G"
    assert item["facts"]["method"] == "MP2"
    assert "version-aware" in item["domain_tags"]
    assert "version_assumption" in item


def test_dft_without_functional_is_blocking(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "input.gjf").write_text(
        "%mem=1GB\n"
        "# DFT/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    payload = preflight_path(case / "input.gjf")
    item = next(d for d in payload["diagnostics"] if d["code"] == CODE_DFT_WITHOUT_FUNCTIONAL)
    assert item["severity"] == "error"
    assert item["blocking"] is True


# --- cross-artifact-graph --------------------------------------------------


def test_artifact_graph_uses_generic_roles() -> None:
    input_path = (FIXTURES / "valid_scf" / "input.gjf").resolve()
    text = input_path.read_text(encoding="utf-8")
    job = _parse(text)
    graph = build_artifact_graph(input_path, job, text)
    roles = {node.role for node in graph.nodes}
    assert roles <= set(ALL_ROLES)
    # primary-input, control, basis, structure are always modeled.
    for required in ("primary-input", "control", "basis", "structure"):
        assert graph.by_role(required), f"missing required role: {required}"
    serialized = graph.to_json()
    assert isinstance(serialized, list)
    assert all("role" in node and "section" in node and "exists" in node for node in serialized)


def test_missing_route_records_role_provenance() -> None:
    payload = preflight_path(FIXTURES / "missing_route" / "input.gjf")
    item = next(d for d in payload["diagnostics"] if d["code"] == CODE_MISSING_ROUTE)
    prov = item["source_provenance"]
    assert prov["role"] == "control"
    assert prov["expected_section"] == "route"


def test_pseudo_with_minimal_basis_is_non_blocking_warning(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "input.gjf").write_text(
        "%mem=1GB\n"
        "# B3LYP/6-31G* pseudo=read gen\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    payload = preflight_path(case / "input.gjf")
    item = next(
        (d for d in payload["diagnostics"] if d["code"] == CODE_PSEUDO_WITHOUT_BASIS),
        None,
    )
    assert item is not None
    assert item["severity"] == "warning"
    assert item["blocking"] is False


def test_opt_maxcycle_disabled_on_optimization_route(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "input.gjf").write_text(
        "%mem=1GB\n"
        "# B3LYP/6-31G* opt=(MaxCycle=1)\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    payload = preflight_path(case / "input.gjf")
    item = next(
        (d for d in payload["diagnostics"] if d["code"] == CODE_OPT_MAXCYCLE_DISABLED),
        None,
    )
    assert item is not None
    assert item["severity"] == "warning"
    assert item["facts"]["maxcycle"] == 1


# --- code-actions / blocking gate -----------------------------------------


def test_check_fail_on_blocking_exits_nonzero_on_failing_fixture() -> None:
    rc = tool.main(["check", str(FIXTURES / "missing_route" / "input.gjf"), "--fail-on-blocking"])
    assert rc == 1


def test_check_fail_on_blocking_exits_zero_on_valid_fixture(capsys) -> None:
    rc = tool.main(["check", str(FIXTURES / "valid_scf" / "input.gjf"), "--fail-on-blocking"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_preflight_subcommand_emits_envelope(capsys) -> None:
    rc = tool.main(["preflight", str(FIXTURES / "low_mem" / "input.gjf")])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "preflight"
    assert payload["diagnostic_envelope"] == "v1"
    assert payload["capabilities"]["operation"] == "preflight"


def test_actions_present_on_blocking_diagnostics() -> None:
    payload = preflight_path(FIXTURES / "missing_basis" / "input.gjf")
    blocking = [d for d in payload["diagnostics"] if d["blocking"]]
    assert blocking
    for item in blocking:
        assert item.get("actions"), f"blocking diagnostic {item['code']} must carry actions"
        assert all("kind" in action for action in item["actions"])


# --- fleet-regression-fixtures / manifest ---------------------------------


def test_manifest_lists_all_four_capabilities() -> None:
    manifest = manifest_path(FIXTURES / "valid_scf" / "input.gjf")
    capabilities = manifest["capabilities"]
    for cap in (
        "version-aware-keywords",
        "cross-artifact-graph",
        "code-actions",
        "fleet-regression-fixtures",
    ):
        assert cap in capabilities, f"missing capability: {cap}"
        assert capabilities[cap]["status"] == "available"
    assert set(manifest["artifact_roles"]) == set(ALL_ROLES)
    assert manifest["preflight_envelope"] == "DiagnosticEnvelope/v1"


def test_manifest_without_path_still_describes_surface() -> None:
    manifest = manifest_path(None)
    assert set(manifest["codes"])
    assert manifest["capabilities"]["code-actions"]["blocking_gate"]


def test_manifest_merges_fixture_expectations() -> None:
    manifest = manifest_path(FIXTURES / "valid_scf" / "input.gjf")
    fixtures = manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"]
    names = {item["name"] for item in fixtures}
    assert {
        "valid_scf",
        "missing_route",
        "missing_basis",
        "guess_read_no_oldchk",
        "low_mem",
        "method_basis_mismatch",
    } <= names


def test_fleet_manifest_helper_pure_data() -> None:
    manifest = fleet_manifest(fixtures=[{"name": "x", "expect_ok": True}])
    assert manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"] == [
        {"name": "x", "expect_ok": True}
    ]
    for body in manifest["codes"].values():
        assert body["severity"] in {"error", "warning", "information", "hint"}
        assert "capability" in body
        assert "summary" in body


def test_fixture_expectations_match_actual_preflight() -> None:
    """The fleet manifest's declared fixture expectations must match reality.

    This is the regression-evidence contract: the parent ``bohrium_skills``
    probe consumes the manifest and replays these fixtures, so the declared
    expectations have to agree with what the preflight actually emits.
    """
    manifest = manifest_path(FIXTURES / "valid_scf" / "input.gjf")
    repo_root = Path(__file__).resolve().parent.parent
    for fixture in manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"]:
        payload = preflight_path(repo_root / fixture["path"])
        assert payload["ok"] is fixture["expect_ok"], (
            f"{fixture['name']}: manifest expects ok={fixture['expect_ok']}, "
            f"got ok={payload['ok']}"
        )
        if fixture["expect_codes"]:
            assert set(fixture["expect_codes"]) <= _envelope_codes(payload), (
                f"{fixture['name']}: expected codes {fixture['expect_codes']}, "
                f"got {sorted(_envelope_codes(payload))}"
            )


# --- dedupe + workspace detection -----------------------------------------


def test_dedupe_preflight_passthrough_when_no_overlap() -> None:
    legacy: list = []
    preflight = [
        {"code": "GAUSSIAN601", "severity": "error", "message": "missing"},
        {"code": "GAUSSIAN606", "severity": "warning", "message": "low mem"},
    ]
    result = _dedupe_preflight(legacy, preflight)
    codes = {item["code"] for item in result}
    assert codes == {"GAUSSIAN601", "GAUSSIAN606"}


def test_looks_like_workspace_requires_gaussian_input(tmp_path: Path) -> None:
    # Empty directory is not a Gaussian workspace.
    assert _looks_like_workspace(tmp_path) is False
    # A bare route fragment (no molecule spec) is intentionally NOT a workspace
    # so the cross-artifact preflight does not fire on a half-typed file the
    # legacy single-file lint already handles.
    fragment = tmp_path / "fragment.gjf"
    fragment.write_text("# B3LYP/6-31G*\n", encoding="utf-8")
    assert _looks_like_workspace(fragment) is False
    # A directory containing a complete route + molecule spec is a workspace.
    real = tmp_path / "input.gjf"
    real.write_text("# B3LYP/6-31G*\n\nwater\n\n0 1\nO 0.0 0.0 0.0\n", encoding="utf-8")
    assert _looks_like_workspace(tmp_path) is True
    assert _looks_like_workspace(real) is True


def test_check_on_workspace_input_merges_preflight(capsys) -> None:
    # Without --fail-on-blocking the CLI exits 0 even though preflight found a
    # blocking issue; the contract here is that the preflight code is merged.
    rc = tool.main(["check", str(FIXTURES / "missing_basis" / "input.gjf")])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    codes = _envelope_codes(payload)
    assert CODE_MISSING_BASIS in codes
    assert payload["diagnostic_envelope"] == "v1"
    assert payload["ok"] is False


def test_artifact_graph_is_json_serializable_for_fleet_report() -> None:
    payload = preflight_path(FIXTURES / "valid_scf" / "input.gjf")
    serialized = json.dumps(payload["artifacts"], sort_keys=True)
    assert "primary-input" in serialized
    assert "structure" in serialized


def test_artifact_graph_class_smoke() -> None:
    graph = ArtifactGraph(input_path=Path("/tmp"))
    assert graph.nodes == []
    assert graph.by_role("structure") == []
    assert graph.to_json() == []


# --- preflight_diagnostics direct API -------------------------------------


def test_preflight_diagnostics_direct_returns_tuple(tmp_path: Path) -> None:
    input_path = tmp_path / "input.gjf"
    input_path.write_text(
        "%mem=1GB\n"
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    diagnostics, graph = preflight_diagnostics(input_path)
    assert isinstance(diagnostics, list)
    assert graph.input_path == input_path.resolve()
    # Version assumption information diagnostic fires when no intent is given.
    assert CODE_VERSION_ASSUMPTION in {d["code"] for d in diagnostics}


def test_unparseable_input_still_builds_minimal_graph(tmp_path: Path) -> None:
    input_path = tmp_path / "input.gjf"
    # A .gjf that fails to parse (no atoms, no charge/mult) still yields a
    # stable graph + a blocking missing-route/structure finding.
    input_path.write_text("just a title\n", encoding="utf-8")
    diagnostics, graph = preflight_diagnostics(input_path)
    codes = {d["code"] for d in diagnostics}
    assert CODE_MISSING_ROUTE in codes
    assert isinstance(graph.to_json(), list)


# --- helper coverage ------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("4GB", 4096.0),
        ("512MB", 512.0),
        ("2000KB", 2000.0 / 1024.0),
        ("1000B", 1000.0 / (1024.0 * 1024.0)),
        ("1000", 1000.0 / (1024.0 * 1024.0)),
        ("4MW", 4 * 1024.0 * 8.0),
        ("8KW", 8 * 1024.0 * 8.0 / (1024.0 * 1024.0)),
        ("2GW", 2 * 1024.0 * 1024.0),
        ("1.5GB", 1.5 * 1024.0),
    ],
)
def test_parse_mem_mb_units(raw: str, expected: float) -> None:
    assert _parse_mem_mb(raw) == pytest.approx(expected)


def test_parse_mem_mb_returns_none_for_unparseable() -> None:
    assert _parse_mem_mb("") is None
    assert _parse_mem_mb("not-a-number") is None


def test_extract_route_int_matches_keyword_value_and_group() -> None:
    assert _extract_route_int("# opt=(MaxCycle=50)", "MaxCycle") == 50
    assert _extract_route_int("# scf=(MaxCycle=99)", "MaxCycle") == 99
    assert _extract_route_int("# B3LYP/6-31G*", "MaxCycle") is None
    assert _extract_route_int("", "MaxCycle") is None


def test_detect_dft_functional_known_and_unknown() -> None:
    assert _detect_dft_functional("# B3LYP/6-31G*").upper() == "B3LYP"
    assert _detect_dft_functional("# PBE0/def2-TZVP").upper() == "PBE0"
    assert _detect_dft_functional("# no method here") is None
    assert _detect_dft_functional("") is None


# --- workspace detection edge cases ---------------------------------------


def test_looks_like_workspace_rejects_nonexistent_and_bare_files(tmp_path: Path) -> None:
    # Non-existent path is not a workspace.
    assert looks_like_gaussian_workspace(tmp_path / "missing.gjf") is False
    # A .txt file (wrong extension) with no route marker is not a workspace.
    txt = tmp_path / "notes.txt"
    txt.write_text("just notes\n0 1\n", encoding="utf-8")
    assert looks_like_gaussian_workspace(txt) is False
    # A .gjf without a route AND without a molecule spec is not a workspace.
    bare = tmp_path / "bare.gjf"
    bare.write_text("just a title\n", encoding="utf-8")
    assert looks_like_gaussian_workspace(bare) is False


def test_looks_like_workspace_accepts_directory_with_complete_input(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "input.gjf").write_text(
        "# B3LYP/6-31G*\n\nwater\n\n0 1\nO 0.0 0.0 0.0\n", encoding="utf-8"
    )
    assert looks_like_gaussian_workspace(case) is True


def test_looks_like_workspace_rejects_directory_with_unrelated_files(tmp_path: Path) -> None:
    case = tmp_path / "case"
    case.mkdir()
    (case / "README.md").write_text("not a gaussian input\n", encoding="utf-8")
    assert looks_like_gaussian_workspace(case) is False


# --- structure / guess / pseudo edge branches -----------------------------


def test_structure_empty_when_molecule_spec_present_but_no_atoms(tmp_path: Path) -> None:
    # Route + charge/mult line but no atom records -> GAUSSIAN602.
    input_path = tmp_path / "input.gjf"
    input_path.write_text("# B3LYP/6-31G*\n\nwater\n\n0 1\n", encoding="utf-8")
    diagnostics, _ = preflight_diagnostics(input_path)
    codes = {d["code"] for d in diagnostics}
    assert CODE_STRUCTURE_EMPTY in codes


def test_guess_read_with_oldchk_is_clean(tmp_path: Path) -> None:
    # guess=read + %oldchk present -> no GAUSSIAN604.
    input_path = tmp_path / "input.gjf"
    input_path.write_text(
        "%oldchk=previous.chk\n"
        "# B3LYP/6-31G* guess=read\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    diagnostics, _ = preflight_diagnostics(input_path)
    assert CODE_GUESS_READ_WITHOUT_OLDCHK not in {d["code"] for d in diagnostics}


def test_pseudo_with_ecp_basis_family_is_clean(tmp_path: Path) -> None:
    # pseudo=read paired with an ECP-capable basis (LANL2DZ) -> no GAUSSIAN605.
    input_path = tmp_path / "input.gjf"
    input_path.write_text(
        "# B3LYP/LANL2DZ pseudo=read gen\n\n" "water\n\n" "0 1\n" "O 0.0 0.0 0.0\n",
        encoding="utf-8",
    )
    diagnostics, _ = preflight_diagnostics(input_path)
    assert CODE_PSEUDO_WITHOUT_BASIS not in {d["code"] for d in diagnostics}


def test_opt_without_maxcycle_is_clean(tmp_path: Path) -> None:
    # OPT job with no explicit MaxCycle -> no GAUSSIAN607 (default is fine).
    input_path = tmp_path / "input.gjf"
    input_path.write_text(
        "# B3LYP/6-31G* opt\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    diagnostics, _ = preflight_diagnostics(input_path)
    assert CODE_OPT_MAXCYCLE_DISABLED not in {d["code"] for d in diagnostics}


def test_low_mem_skipped_when_mem_unparseable(tmp_path: Path) -> None:
    # An unparseable %mem value does not crash preflight and emits no GAUSSIAN606.
    input_path = tmp_path / "input.gjf"
    input_path.write_text(
        "%mem=not-a-number\n"
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    diagnostics, _ = preflight_diagnostics(input_path)
    assert CODE_LOW_MEM not in {d["code"] for d in diagnostics}


def test_low_mem_skipped_when_no_mem_declared(tmp_path: Path) -> None:
    # No %mem at all -> no GAUSSIAN606.
    input_path = tmp_path / "input.gjf"
    input_path.write_text(
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    diagnostics, _ = preflight_diagnostics(input_path)
    assert CODE_LOW_MEM not in {d["code"] for d in diagnostics}


def test_manifest_path_handles_directory(tmp_path: Path) -> None:
    # manifest_path on a directory merges fixtures.json from .gaussian-lsp/.
    case = tmp_path / "case"
    cfg = case / ".gaussian-lsp"
    cfg.mkdir(parents=True)
    (cfg / "fixtures.json").write_text(
        json.dumps({"fixtures": [{"name": "x", "expect_ok": True}]}),
        encoding="utf-8",
    )
    manifest = manifest_path(case)
    assert manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"] == [
        {"name": "x", "expect_ok": True}
    ]


def test_manifest_path_returns_surface_when_fixtures_unparseable(tmp_path: Path) -> None:
    case = tmp_path / "case"
    cfg = case / ".gaussian-lsp"
    cfg.mkdir(parents=True)
    (cfg / "fixtures.json").write_text("not json", encoding="utf-8")
    manifest = manifest_path(case)
    assert manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"] == []


def test_intent_loaded_for_case_directory(tmp_path: Path) -> None:
    # The intent contract is loaded from .gaussian-lsp/intent.json next to the
    # input; when it declares a software_version, the version-assumption
    # information diagnostic stays silent.
    case = tmp_path / "case"
    cfg = case / ".gaussian-lsp"
    cfg.mkdir(parents=True)
    (case / "input.gjf").write_text(
        "%mem=1GB\n"
        "# B3LYP/6-31G*\n\n"
        "water\n\n"
        "0 1\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.0 1.0\n"
        "H 0.0 1.0 0.0\n",
        encoding="utf-8",
    )
    (cfg / "intent.json").write_text(
        json.dumps({"software_version": "gaussian >=g16"}), encoding="utf-8"
    )
    payload = preflight_path(case / "input.gjf")
    assert CODE_VERSION_ASSUMPTION not in _envelope_codes(payload)


def test_preflight_fail_on_blocking_exits_nonzero(capsys) -> None:
    rc = tool.main(
        ["preflight", str(FIXTURES / "missing_route" / "input.gjf"), "--fail-on-blocking"]
    )
    assert rc == 1


def test_manifest_subcommand_emits_envelope(capsys) -> None:
    rc = tool.main(["manifest"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["preflight_envelope"] == "DiagnosticEnvelope/v1"
    assert "code-actions" in payload["capabilities"]
