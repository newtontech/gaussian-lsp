"""Closed-loop fixture tests for agent CLI and DiagnosticEnvelope/v1.

Covers issue #80: valid/invalid golden fixtures, fix previews, manifest/smoke
evidence, and stable envelope JSON from ``gaussian-lsp-tool check``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaussian_lsp import tool

FIXTURES = Path(__file__).parent / "fixtures"
RULES = FIXTURES / "rules"
LOG_FIXTURES = FIXTURES / "log"


class TestDiagnosticEnvelopeV1:
    @pytest.mark.parametrize(
        "fixture",
        ["water_sp.gjf", "formaldehyde_opt_freq.gjf"],
    )
    def test_valid_fixtures_have_no_blocking_diagnostics(self, fixture: str, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "valid" / fixture)])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["diagnostic_envelope"] == "v1"
        assert payload["diagnostic_engine"] == "1.0"
        assert payload["software"] == "gaussian"
        blocking = [d for d in payload["diagnostics"] if d.get("blocking")]
        assert blocking == [], f"unexpected blocking: {blocking}"

    def test_invalid_missing_charge_mult_has_blocking_error(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "invalid" / "missing_charge_mult.gjf")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["diagnostic_envelope"] == "v1"
        assert payload["ok"] is False
        blocking = [d for d in payload["diagnostics"] if d.get("blocking")]
        assert len(blocking) >= 1
        assert any(d.get("severity") == "error" for d in blocking)

    def test_invalid_unknown_route_has_warning(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "invalid" / "unknown_route_keyword.gjf")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        warnings = [d for d in payload["diagnostics"] if d.get("severity") in {"warning", "hint"}]
        assert warnings, "expected at least one advisory diagnostic"

    def test_diagnostics_carry_envelope_fields(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "invalid" / "low_memory_nproc.gjf")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        for diag in payload["diagnostics"]:
            assert "code" in diag
            assert "severity" in diag
            assert "blocking" in diag
            assert "range" in diag
            assert diag.get("diagnostic_envelope") == "v1"


class TestFixOperation:
    def test_fix_returns_preview_actions(self, capsys) -> None:
        rc = tool.main(["fix", str(FIXTURES / "invalid" / "missing_charge_mult.gjf")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["capabilities"]["operation"] == "fix"
        assert "actions" in payload
        assert isinstance(payload["actions"], list)

    def test_fix_on_valid_fixture_is_empty(self, capsys) -> None:
        rc = tool.main(["fix", str(FIXTURES / "valid" / "water_sp.gjf")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["actions"] == []


class TestRuleFixtureCatalog:
    @pytest.mark.parametrize("rule_file", sorted(RULES.glob("*.json")))
    def test_rule_fixture_documents_expected_codes(self, rule_file: Path) -> None:
        spec = json.loads(rule_file.read_text(encoding="utf-8"))
        assert "rule" in spec
        assert "code" in spec
        assert "expected" in spec
        assert spec["expected"]["code"] == spec["code"]


class TestOpenQCSmokeEvidence:
    REQUIRED_OPENQC_FIELDS = ("lsp_check_family", "compatibility_report_entry")

    def test_lsp_capabilities_has_provenance_and_openqc(self) -> None:
        caps_path = Path(__file__).parent.parent / "lsp-capabilities.json"
        payload = json.loads(caps_path.read_text(encoding="utf-8"))
        assert payload["openqc"]["lsp_check_family"] is True
        assert len(payload.get("sourceProvenance", [])) >= 1

    def test_lsp_capabilities_manifest_has_fleet_capabilities_section(self) -> None:
        caps_path = Path(__file__).parent.parent / "lsp-capabilities.json"
        payload = json.loads(caps_path.read_text(encoding="utf-8"))

        assert payload["languageId"] == "gaussian"
        assert payload["repository"] == "newtontech/gaussian-lsp"
        assert payload.get("version") or payload.get("capabilities_version")

        capabilities = payload.get("capabilities")
        assert isinstance(capabilities, list) and capabilities, "capabilities section required"
        for required in (
            "agent-envelope",
            "agent-json-cli",
            "diagnostic-engine-v1",
            "diagnostics",
            "openqc-context",
            "source-provenance",
        ):
            assert required in capabilities, f"missing fleet capability: {required}"

        openqc = payload.get("openqc", {})
        for field in self.REQUIRED_OPENQC_FIELDS:
            assert field in openqc and openqc[field], f"missing openqc.{field}"

        agent_cli = payload.get("agentCli", {})
        assert agent_cli.get("command") == "gaussian-lsp-tool"
        assert "check" in agent_cli.get("operations", [])
        assert payload.get("diagnostic_coverage", {}).get("status") == "partial"

    def test_raw_assets_manifest_exists(self) -> None:
        manifest = Path(__file__).parent.parent / "raw/assets/manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert len(data.get("entries", [])) >= 1

    def test_manifest_operation_emits_fleet_manifest(self, capsys) -> None:
        rc = tool.main(["manifest"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "capabilities" in payload
        assert "codes" in payload

    def test_fail_on_blocking_exits_nonzero_for_invalid_fixture(self, capsys) -> None:
        rc = tool.main(
            ["check", str(FIXTURES / "invalid" / "missing_charge_mult.gjf"), "--fail-on-blocking"]
        )
        assert rc == 1

    def test_log_fixtures_exist_for_runtime_diagnostics(self) -> None:
        """The Python runtime log parser (issue #87) extends the log fixture
        surface beyond the original scf_not_converged/scf_converged pair."""
        assert (LOG_FIXTURES / "scf_not_converged.out").exists()
        assert (LOG_FIXTURES / "scf_converged.out").exists()
        # The runtime-log capability ships at least three additional realistic
        # failure-mode fixtures (SCF L502, basis L301, optimization L103/L9999,
        # memory exhaustion, geometry parse failure).
        for fixture in (
            "error_termination_l502.log",
            "error_termination_l301.log",
            "optimization_not_converged.log",
            "memory_exhausted.log",
            "geometry_parse_failure.log",
            "normal_termination.out",
        ):
            assert (LOG_FIXTURES / fixture).exists(), f"missing log fixture: {fixture}"

    def test_parse_log_cli_returns_v1_envelope(self, capsys) -> None:
        """The parse-log CLI subcommand is part of the closed-loop contract."""
        rc = tool.main(["parse-log", str(LOG_FIXTURES / "scf_not_converged.out")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["diagnostic_envelope"] == "v1"
        assert payload["operation"] == "parse-log"
        assert payload["software"] == "gaussian"
        assert payload["ok"] is False


class TestReleaseProvenance:
    REPO_ROOT = Path(__file__).resolve().parent.parent

    def test_version_file_matches_capabilities_and_pyproject(self) -> None:
        version_text = (self.REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        capabilities = json.loads(
            (self.REPO_ROOT / "lsp-capabilities.json").read_text(encoding="utf-8")
        )
        pyproject = (self.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        assert version_text == capabilities["version"]
        assert f'version = "{version_text}"' in pyproject
        assert capabilities["release_provenance"]["version_file"] == "VERSION"
        assert capabilities["release_provenance"]["changelog"] == "CHANGELOG.md"

    def test_release_provenance_documents_closed_loop_support(self) -> None:
        capabilities = json.loads(
            (self.REPO_ROOT / "lsp-capabilities.json").read_text(encoding="utf-8")
        )
        release = capabilities["release_provenance"]
        assert release["supported_gaussian_versions"] == ["Gaussian 16"]
        assert release["closed_loop_support"]["log_diagnostics"] is True
        assert release["closed_loop_support"]["fix_previews"] is True
        assert release["closed_loop_support"]["requires_binary"] is False
