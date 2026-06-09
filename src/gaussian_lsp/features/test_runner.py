"""Optional test-runner / dry-run bridge for Gaussian."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range


@dataclass
class TestRunnerConfig:
    executable: str = ""
    timeout: float = 30.0
    enabled: bool = False
    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.enabled and not self.executable:
            errors.append("Gaussian executable path is not configured")
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        return errors


@dataclass
class SolverOutput:
    success: bool = True
    raw_output: str = ""
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)


_ERROR_PATTERNS = [
    (re.compile(r"Error:\s*(.+?)(?:\n|$)", re.MULTILINE), "error"),
    (re.compile(r"Warning:\s*(.+?)(?:\n|$)", re.MULTILINE), "warning"),
    (re.compile(r"ReqM\s+.*?not found", re.MULTILINE), "error"),
]

_LINE_NUM_RE = re.compile(r"line\s+(\d+)", re.IGNORECASE)


def parse_solver_output(raw: str) -> SolverOutput:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    for pattern, severity in _ERROR_PATTERNS:
        for match in pattern.finditer(raw):
            message = match.group(0).strip()
            line_num = 0
            line_match = _LINE_NUM_RE.search(message)
            if line_match:
                line_num = int(line_match.group(1)) - 1
            entry = {"message": message, "line": line_num, "source": "gaussian-test-runner"}
            (errors if severity == "error" else warnings).append(entry)
    return SolverOutput(success=len(errors) == 0, raw_output=raw, errors=errors, warnings=warnings)


def solver_output_to_diagnostics(output: SolverOutput) -> List[Diagnostic]:
    diags: List[Diagnostic] = []
    for e in output.errors:
        diags.append(Diagnostic(
            range=Range(start=Position(e["line"], 0), end=Position(e["line"], 999)),
            message=e["message"], severity=DiagnosticSeverity.Error,
            source="gaussian-test-runner", code="Gauss9001"))
    for w in output.warnings:
        diags.append(Diagnostic(
            range=Range(start=Position(w["line"], 0), end=Position(w["line"], 999)),
            message=w["message"], severity=DiagnosticSeverity.Warning,
            source="gaussian-test-runner", code="Gauss9002"))
    return diags


class TestRunnerProvider:
    def __init__(self, config: Optional[TestRunnerConfig] = None) -> None:
        self._config = config or TestRunnerConfig()

    @property
    def config(self) -> TestRunnerConfig:
        return self._config

    @config.setter
    def config(self, value: TestRunnerConfig) -> None:
        self._config = value

    def validate_config(self) -> List[str]:
        return self._config.validate()

    def run_validation(self, source: str) -> List[Diagnostic]:
        if not self._config.enabled:
            return [Diagnostic(range=Range(start=Position(0, 0), end=Position(0, 0)),
                message="Gaussian test runner not enabled.", severity=DiagnosticSeverity.Information,
                source="gaussian-test-runner", code="Gauss9000")]
        if not self._config.executable:
            return [Diagnostic(range=Range(start=Position(0, 0), end=Position(0, 0)),
                message="Gaussian executable not configured.", severity=DiagnosticSeverity.Warning,
                source="gaussian-test-runner", code="Gauss9000")]
        import shutil
        if not shutil.which(self._config.executable):
            return [Diagnostic(range=Range(start=Position(0, 0), end=Position(0, 0)),
                message=f"Gaussian executable not found: {self._config.executable}",
                severity=DiagnosticSeverity.Error, source="gaussian-test-runner", code="Gauss9000")]
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".gjf", delete=False) as f:
                f.write(source)
                temp_path = f.name
            result = subprocess.run([self._config.executable, temp_path],
                capture_output=True, text=True, timeout=self._config.timeout)
            return solver_output_to_diagnostics(parse_solver_output(result.stdout + "\n" + result.stderr))
        except subprocess.TimeoutExpired:
            return [Diagnostic(range=Range(start=Position(0, 0), end=Position(0, 0)),
                message=f"Gaussian timed out after {self._config.timeout}s.",
                severity=DiagnosticSeverity.Warning, source="gaussian-test-runner", code="Gauss9003")]
        except FileNotFoundError:
            return [Diagnostic(range=Range(start=Position(0, 0), end=Position(0, 0)),
                message=f"Gaussian not found: {self._config.executable}",
                severity=DiagnosticSeverity.Error, source="gaussian-test-runner", code="Gauss9000")]
        finally:
            try: Path(temp_path).unlink()
            except (NameError, FileNotFoundError): pass

    def run_with_captured_output(self, captured_output: str) -> List[Diagnostic]:
        return solver_output_to_diagnostics(parse_solver_output(captured_output))

    def snapshot_config(self) -> str:
        return json.dumps({"enabled": self._config.enabled,
            "executable": self._config.executable or "(not configured)",
            "timeout": self._config.timeout}, indent=2)
