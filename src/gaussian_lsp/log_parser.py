"""Gaussian runtime output parser (DiagnosticEnvelope/v1).

This module closes the backend-only parity gap with the TypeScript ``parseLog``
surface: it parses real Gaussian ``.log``/``.out`` runtime output and emits
DiagnosticEnvelope/v1-shaped findings, with fixture-derived provenance and
explicit safe-to-auto-apply / refusal-reason metadata.

Rule code namespace
~~~~~~~~~~~~~~~~~~~

The codes align with the existing TypeScript rule codes (GAUSS-E034/E035) and
extend the runtime surface with the four failure modes cclib + the Gaussian
community treat as the most common production failures:

- **GAUSS-E034** ``gaussian.log.scf_not_converged`` -- SCF iteration limit hit
- **GAUSS-E035** ``gaussian.log.geometry_parse_failure`` -- geometry / Z-matrix
  parse failure in L101
- **GAUSS-E036** ``gaussian.log.error_termination`` -- ``Error termination via
  Lnk1e`` (catch-all fatal termination reported by the Gaussian supervisor)
- **GAUSS-E037** ``gaussian.log.link_fault`` -- structured per-Link fault with
  the offending Link name (l101, l301, l502, l716, l9999, ...)
- **GAUSS-E038** ``gaussian.log.opt_not_converged`` -- ``Optimization stopped``
  or NStep exhausted during geometry optimisation
- **GAUSS-E039** ``gaussian.log.memory_exhausted`` -- ``Not enough memory`` /
  ``insufficient memory`` during resource allocation
- **GAUSS-W034** ``gaussian.log.opt_step_unconverged`` -- ``Item ... NO``
  convergence line (non-fatal when followed by another step)

Provenance
~~~~~~~~~~

Every finding carries ``source_provenance`` pointing at the fixture-derived
snippet + the wiki/spec source. The Gaussian runtime output grammar is not
formally specified; the patterns here are derived from the
``raw/assets/gaussian-output-format.md`` evidence + cclib's gaussianparser.py
behaviour and validated against the fixtures in ``tests/fixtures/log``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .rich_diagnostics import DIAGNOSTIC_ENVELOPE_VERSION

# ---------------------------------------------------------------------------
# Rule code namespace
# ---------------------------------------------------------------------------

#: SCF iteration limit hit (parity with TS diagnostics.ts).
CODE_SCF_NOT_CONVERGED = "GAUSS-E034"
#: Geometry / Z-matrix parse failure (parity with TS diagnostics.ts).
CODE_GEOMETRY_PARSE_FAILURE = "GAUSS-E035"
#: ``Error termination via Lnk1e`` -- catch-all fatal termination marker.
CODE_ERROR_TERMINATION = "GAUSS-E036"
#: Structured per-Link fault with the offending Link executable name.
CODE_LINK_FAULT = "GAUSS-E037"
#: Geometry optimisation step count exhausted / did not converge.
CODE_OPT_NOT_CONVERGED = "GAUSS-E038"
#: Memory or disk exhaustion reported by the runtime.
CODE_MEMORY_EXHAUSTED = "GAUSS-E039"
#: ``Item ... NO`` optimisation convergence line -- warning, not fatal.
CODE_OPT_STEP_UNCONVERGED = "GAUSS-W034"

#: All public log parser codes, ordered by severity then rule id.
ALL_LOG_CODES: tuple[str, ...] = (
    CODE_SCF_NOT_CONVERGED,
    CODE_GEOMETRY_PARSE_FAILURE,
    CODE_ERROR_TERMINATION,
    CODE_LINK_FAULT,
    CODE_OPT_NOT_CONVERGED,
    CODE_MEMORY_EXHAUSTED,
    CODE_OPT_STEP_UNCONVERGED,
)

# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------

# Lines are matched case-insensitively. Each pattern carries a stable rule
# id so callers can correlate finding <-> matcher for fleet provenance.

#: ``Error termination via Lnk1e in /scr1/g16/l502.exe at <date>``.  We capture
#: the link executable so the GAUSS-E037 finding can name the failing Link.
#: We accept two surface forms:
#:   * the canonical supervisor form ``Error termination via Lnk1e in /path/l502.exe``
#:   * the abbreviated form ``Error termination via L502.`` (used by minimal fixtures
#:     that mirror the marker without the full path).
_ERROR_TERMINATION_SUPERVISOR_RE = re.compile(
    r"Error termination via\s+(?P<link_supervisor>Lnk1[a-z])\s+in\s+"
    r"(?P<link_path>\S+/l(?P<link_num>\d+)\.exe)",
    re.IGNORECASE,
)
_ERROR_TERMINATION_ABBREVIATED_RE = re.compile(
    r"Error termination via\s+L(?P<abbrev_num>\d+)\b",
    re.IGNORECASE,
)

#: ``Convergence failure -- SCF cycle limit reached.`` and the
#: ``SCF fails to converge after N cycles`` variant.
_SCF_CONVERGENCE_FAILURE_RE = re.compile(
    r"Convergence failure\b|SCF\s+fails\s+to\s+converge", re.IGNORECASE
)

#: ``SCF Done:  E(RB3LYP) =  -76.12345 A.U. after  50 cycles`` -- used as
#: provenance metadata (cycles + energy label) for SCF convergence findings.
_SCF_DONE_RE = re.compile(
    r"SCF Done:\s+E\((?P<method>[^)]+)\)\s*=\s*(?P<energy>-?\d+\.\d+)"
    r"\s+A\.U\.\s+after\s+(?P<cycles>\d+)\s+cycles",
    re.IGNORECASE,
)

#: ``Error in geometry specification.`` / ``Input Error: ...``.
_GEOMETRY_ERROR_RE = re.compile(r"Error in geometry|Input Error|Stop in parsing", re.IGNORECASE)

#: ``Optimization stopped.`` and ``Number of steps exceeded, NStep= 50``.
#: Gaussian splits this across two lines on the canonical output, so the
#: matcher captures the ``NStep=N`` group from *either* the same line (the
#: two-line canonical form joins them in some tooling) or the same log line
#: (GaussView/cclib sometimes collapse them). The bare ``Optimization stopped``
#: and bare ``Number of steps exceeded`` patterns are kept as alternations so
#: a single-line form still triggers GAUSS-E038.
_OPT_STOPPED_RE = re.compile(
    r"Optimization stopped(?:\.\s*--\s*Number of steps exceeded,\s*NStep=\s*(?P<nstep>\d+))?"
    r"|Number of steps exceeded(?:,\s*NStep=\s*(?P<nstep_alt>\d+))?",
    re.IGNORECASE,
)

#: ``Item ... Maximum Force   0.000144   0.000045   NO`` -- non-fatal warning
#: while the optimisation is still iterating.
_OPT_ITEM_UNCONVERGED_RE = re.compile(
    r"^\s*(?:Item|Maximum\s+Force|RMS\s+Force|Maximum\s+Displacement|RMS\s+Displacement)" r".*NO\b",
    re.IGNORECASE,
)

#: ``Not enough memory`` / ``insufficient memory`` / ``Wanted XXX, got YYY``.
_MEMORY_EXHAUSTED_RE = re.compile(
    r"Not enough memory|insufficient memory|Wanted\s+\S+\s+bytes?\s+of\s+mem",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Link directory -- maps the offending link number to a human-readable role.
# Source: raw/assets/gaussian-output-format.md (Link table) + cclib.
# ---------------------------------------------------------------------------

#: Map from Gaussian Link number -> (role, common_cause) used to populate
#: ``facts`` and ``fix_hints`` on GAUSS-E037 findings.
LINK_KNOWLEDGE: dict[int, dict[str, str]] = {
    101: {
        "role": "title/charge/multiplicity",
        "cause": (
            "Link 101 (title/molecule read) rejected the charge/multiplicity "
            "or molecule specification lines."
        ),
        "hint": (
            "Verify the charge/multiplicity line matches the atom list and "
            "that Z-matrix variables are defined."
        ),
    },
    103: {
        "role": "geometry optimization",
        "cause": (
            "Link 103 (Berny optimization) failed an optimization step -- "
            "commonly a bad initial Hessian or runaway step."
        ),
        "hint": (
            "Recompute the initial Hessian (opt=calcfc) or tighten/optimize "
            "the starting geometry."
        ),
    },
    202: {
        "role": "coordinate standardization",
        "cause": (
            "Link 202 (standard orientation/symmetry) failed while " "reorienting the molecule."
        ),
        "hint": ("Add nosymm to the route to disable symmetry, or simplify the " "input geometry."),
    },
    301: {
        "role": "basis set specification",
        "cause": (
            "Link 301 (basis/pseudopotential read) could not resolve the "
            "basis set or gen block for one or more atoms."
        ),
        "hint": (
            "Check the basis spelling, the gen block, and that every atom "
            "has a basis/ECP entry when genecp is used."
        ),
    },
    402: {
        "role": "Z-matrix internal coordinates",
        "cause": "Link 402 (Z-matrix) failed parsing the internal coordinates.",
        "hint": "Switch to cartesian input or fix the Z-matrix references.",
    },
    502: {
        "role": "SCF iteration",
        "cause": (
            "Link 502 (SCF iteration) failed -- typically DIIS divergence "
            "or a poor initial guess."
        ),
        "hint": ("Try scf=(xqc, maxcycle=128), a better guess, or fragmentation."),
    },
    716: {
        "role": "first derivatives",
        "cause": "Link 716 (gradient) failed computing first derivatives.",
        "hint": "Reduce the integration grid or check the method/basis.",
    },
    9999: {
        "role": "termination / archive",
        "cause": (
            "Link 9999 (archive write) reported the run as failed -- often "
            "an upstream step (optimization steps, convergence) hit a limit."
        ),
        "hint": "Increase MaxCycle or verify the optimization converged.",
    },
}


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogFinding:
    """A single runtime finding extracted from a Gaussian log.

    The dataclass exists for testability; ``to_dict`` produces the
    DiagnosticEnvelope/v1-compatible payload.
    """

    code: str
    severity: str
    message: str
    line: int  # 1-based
    column: int = 1
    category: str = "preflight/runtime-risk"
    confidence: float = 0.9
    blocking: bool = True
    source: str = "gaussian-log-parser"
    facts: dict[str, Any] | None = None
    # ``Sequence`` accepts lists and tuples so callers can write the more
    # natural ``["hint", "hint"]`` instead of ``("hint", "hint")``.
    fix_hints: Sequence[str] = ()
    actions: Sequence[dict[str, Any]] = ()
    artifact_roles: Sequence[str] = ("runtime-output",)
    source_provenance: dict[str, Any] | None = None
    manual_ref: str | None = None
    refusal_reason: str | None = None

    def to_dict(self, *, path: str = "") -> dict[str, Any]:
        line0 = max(self.line - 1, 0)
        col0 = max(self.column - 1, 0)
        payload: dict[str, Any] = {
            "diagnostic_engine": "1.0",
            "diagnostic_envelope": DIAGNOSTIC_ENVELOPE_VERSION,
            "code": self.code,
            "severity": self.severity,
            "category": self.category,
            "confidence": self.confidence,
            "source": self.source,
            "range": {
                "start": {"line": line0, "character": col0},
                "end": {"line": line0, "character": col0 + 1},
            },
            "software": "gaussian",
            "file_type": "log",
            "path": path,
            "blocking": self.blocking,
            "fix_hints": list(self.fix_hints),
            "message": self.message,
        }
        if self.facts:
            payload["facts"] = dict(self.facts)
        if self.actions:
            payload["actions"] = list(self.actions)
        if self.artifact_roles:
            payload["artifact_roles"] = list(self.artifact_roles)
        if self.source_provenance:
            payload["source_provenance"] = dict(self.source_provenance)
        if self.manual_ref:
            payload["manual_ref"] = self.manual_ref
        if self.refusal_reason:
            payload["refusal_reason"] = self.refusal_reason
        return payload


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_log(text: str, *, path: str = "") -> list[dict[str, Any]]:
    """Parse Gaussian ``.log``/``.out`` text and return v1-shaped diagnostics.

    The function is the Python-side parity for the TypeScript ``parseLog`` in
    ``src/parsers/diagnostics.ts``. It extends the surface to cover the four
    production failure modes most fleet consumers care about: SCF convergence,
    geometry/Link errors, optimization exhaustion, and memory/disk exhaustion.

    Args:
        text: Raw Gaussian log/output text.
        path: Optional path string stamped on every diagnostic.

    Returns:
        A deterministically sorted list of DiagnosticEnvelope/v1 dicts.
    """
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()

    last_scf_done: dict[str, Any] | None = None
    saw_error_termination = False

    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()

        # Track the most recent SCF Done so convergence-failure findings can
        # carry the energy/method/cycles facts as provenance.
        scf_match = _SCF_DONE_RE.search(stripped)
        if scf_match:
            last_scf_done = {
                "method": scf_match.group("method"),
                "energy": float(scf_match.group("energy")),
                "cycles": int(scf_match.group("cycles")),
                "line": lineno,
            }

        # GAUSS-E036: catch-all fatal termination marker.
        # GAUSS-E037: structured per-Link fault with the link executable.
        et_supervisor = _ERROR_TERMINATION_SUPERVISOR_RE.search(stripped)
        et_abbrev = (
            _ERROR_TERMINATION_ABBREVIATED_RE.search(stripped) if et_supervisor is None else None
        )
        et_match = et_supervisor or et_abbrev
        if et_match:
            saw_error_termination = True
            if et_supervisor is not None:
                link_num = int(et_supervisor.group("link_num"))
                link_path = et_supervisor.group("link_path")
                supervisor = et_supervisor.group("link_supervisor")
            else:
                # Abbreviated form: ``Error termination via L301.`` -- the
                # link number is in the ``abbrev_num`` group; we synthesize
                # a stable link identifier for provenance.
                assert et_abbrev is not None  # for mypy
                link_num = int(et_abbrev.group("abbrev_num"))
                link_path = f"l{link_num}.exe"
                supervisor = "L{0}".format(link_num)
            knowledge = LINK_KNOWLEDGE.get(
                link_num,
                {
                    "role": "unknown",
                    "cause": (f"Link l{link_num} reported a fatal termination."),
                    "hint": (
                        f"Inspect the surrounding l{link_num} log section for "
                        "the immediate cause."
                    ),
                },
            )
            # Emit the structured Link fault first so consumers can branch.
            findings.append(
                _link_finding(
                    lineno=lineno,
                    raw_line=stripped,
                    link_num=link_num,
                    link_path=link_path,
                    supervisor=supervisor,
                    role=knowledge["role"],
                    cause=knowledge["cause"],
                    hint=knowledge["hint"],
                    path=path,
                )
            )
            # The supervisor-line finding itself is the catch-all marker. We
            # only emit it once per file (Gaussian always emits exactly one
            # Error termination per fatal job, but be defensive).
            if not any(item["code"] == CODE_ERROR_TERMINATION for item in findings):
                findings.append(
                    LogFinding(
                        code=CODE_ERROR_TERMINATION,
                        severity="error",
                        message=(
                            "Gaussian supervisor reported fatal 'Error "
                            "termination' -- the job did not complete"
                        ),
                        line=lineno,
                        category="preflight/runtime-risk",
                        confidence=0.99,
                        blocking=True,
                        artifact_roles=("runtime-output", "control"),
                        facts={
                            "supervisor": supervisor,
                            "link_executable": link_path,
                            "link_number": link_num,
                        },
                        fix_hints=[
                            "Open the log and locate the line above 'Error "
                            "termination' for the immediate cause",
                            "Cross-reference the Link number (e.g. l502) "
                            "with the Gaussian Link table to narrow the cause",
                        ],
                        actions=[
                            {
                                "kind": "open_log_context",
                                "target": path,
                                "line": lineno,
                                "safe_to_auto_apply": False,
                                "refusal_reason": (
                                    "Cannot auto-repair runtime termination: "
                                    "the cause is upstream of the supervisor "
                                    "line and requires manual log inspection."
                                ),
                            }
                        ],
                        source_provenance=_log_provenance(
                            raw_line=stripped,
                            rule=CODE_ERROR_TERMINATION,
                            source="raw/assets/gaussian-output-format.md",
                            note=(
                                "Gaussian supervisor emits exactly one "
                                "'Error termination via Lnk1e' line per fatal "
                                "job; the link executable names the failing "
                                "stage."
                            ),
                        ),
                        manual_ref=(
                            "https://gaussian.com/overlay1/  " "(Link numbering reference)"
                        ),
                        refusal_reason=(
                            "Cannot auto-repair runtime termination without "
                            "manual log inspection."
                        ),
                    ).to_dict(path=path)
                )

        # GAUSS-E034: SCF convergence failure.
        if _SCF_CONVERGENCE_FAILURE_RE.search(stripped):
            findings.append(
                _scf_convergence_finding(
                    lineno=lineno,
                    raw_line=stripped,
                    last_scf_done=last_scf_done,
                    path=path,
                )
            )

        # GAUSS-E035: geometry / Z-matrix / input error.
        if _GEOMETRY_ERROR_RE.search(stripped):
            findings.append(_geometry_error_finding(lineno, stripped, path=path))

        # GAUSS-E038: optimization stopped (fatal -- NStep exhausted).
        # Gaussian splits this across two canonical lines; capture the
        # NStep=N from either the same line or the line that follows.
        opt_match = _OPT_STOPPED_RE.search(stripped)
        if opt_match:
            gd = opt_match.groupdict()
            nstep_str = gd.get("nstep") or gd.get("nstep_alt")
            nstep: int | None
            if nstep_str and str(nstep_str).isdigit():
                nstep = int(nstep_str)
            else:
                # Look ahead at the next line for ``-- Number of steps
                # exceeded, NStep=N`` so we can still record the budget.
                if lineno < len(lines):
                    ahead = lines[lineno].strip()  # next line (0-indexed)
                    ahead_match = re.search(r"NStep=\s*(\d+)", ahead, re.IGNORECASE)
                    nstep = (
                        int(ahead_match.group(1))
                        if ahead_match and ahead_match.group(1).isdigit()
                        else None
                    )
                else:
                    nstep = None
            findings.append(_opt_stopped_finding(lineno, stripped, nstep, path=path))

        # GAUSS-E039: memory / disk exhaustion.
        if _MEMORY_EXHAUSTED_RE.search(stripped):
            findings.append(_memory_exhausted_finding(lineno, stripped, path=path))

        # GAUSS-W034: optimisation step convergence line says NO. This is a
        # per-iteration warning, not fatal -- unless the run terminates.
        if _OPT_ITEM_UNCONVERGED_RE.match(stripped):
            findings.append(_opt_step_unconverged_finding(lineno, stripped, path=path))

    # The runtime diagnostic surface always reports whether the run reached a
    # 'Normal termination' so the parent fleet probe can branch. We emit it as
    # an information-level finding (no blocking) when there are blocking
    # findings but no 'Normal termination' marker.
    has_normal_termination = any("Normal termination" in line for line in lines)
    if not has_normal_termination and not saw_error_termination and not findings:
        # Empty log or no terminators -- emit an information diagnostic so the
        # parent probe has at least one finding to gate on.
        findings.append(
            LogFinding(
                code="GAUSS-I031",
                severity="information",
                message=(
                    "No 'Normal termination' or 'Error termination' marker "
                    "found; the log may be truncated or incomplete."
                ),
                line=1,
                category="preflight/runtime-risk",
                confidence=0.6,
                blocking=False,
                artifact_roles=("runtime-output",),
                fix_hints=[
                    "Re-fetch the log from the runtime and confirm the job " "actually exited."
                ],
                source_provenance=_log_provenance(
                    raw_line="",
                    rule="GAUSS-I031",
                    source="raw/assets/gaussian-output-format.md",
                    note=(
                        "Gaussian always emits a final termination marker; "
                        "absence indicates truncation."
                    ),
                ),
            ).to_dict(path=path)
        )

    # Stable sort: blocking first, then by line, then by code.
    findings.sort(
        key=lambda f: (
            0 if f["blocking"] else 1,
            f["range"]["start"]["line"],
            f["code"],
        )
    )
    return findings


# ---------------------------------------------------------------------------
# Fleet manifest helper
# ---------------------------------------------------------------------------


def log_manifest() -> dict[str, Any]:
    """Return the runtime-log capability manifest for the parent fleet probe.

    Mirrors the shape of :func:`gaussian_lsp.preflight.fleet_manifest` so the
    parent router can branch on either surface without bespoke logic.
    """
    codes = {
        CODE_SCF_NOT_CONVERGED: {
            "severity": "error",
            "category": "preflight/runtime-risk",
            "blocking": True,
            "capability": "runtime-log",
            "summary": "SCF cycle limit reached (L502 convergence failure)",
        },
        CODE_GEOMETRY_PARSE_FAILURE: {
            "severity": "error",
            "category": "syntax",
            "blocking": True,
            "capability": "runtime-log",
            "summary": "Geometry / Z-matrix / input parse failure in L101/L402",
        },
        CODE_ERROR_TERMINATION: {
            "severity": "error",
            "category": "preflight/runtime-risk",
            "blocking": True,
            "capability": "runtime-log",
            "summary": "'Error termination via Lnk1e' supervisor marker",
        },
        CODE_LINK_FAULT: {
            "severity": "error",
            "category": "preflight/runtime-risk",
            "blocking": True,
            "capability": "runtime-log",
            "summary": "Structured per-Link fault with executable name",
        },
        CODE_OPT_NOT_CONVERGED: {
            "severity": "error",
            "category": "preflight/runtime-risk",
            "blocking": True,
            "capability": "runtime-log",
            "summary": "Optimization step count exhausted (NStep)",
        },
        CODE_MEMORY_EXHAUSTED: {
            "severity": "error",
            "category": "preflight/runtime-risk",
            "blocking": True,
            "capability": "runtime-log",
            "summary": "Runtime memory / disk exhaustion",
        },
        CODE_OPT_STEP_UNCONVERGED: {
            "severity": "warning",
            "category": "semantic consistency",
            "blocking": False,
            "capability": "runtime-log",
            "summary": "'Item ... NO' optimisation convergence line",
        },
    }
    return {
        "software": "gaussian",
        "log_envelope": "DiagnosticEnvelope/v1",
        "capability": "runtime-log",
        "status": "available",
        "codes": codes,
        "link_map": {
            str(num): {"role": data["role"], "hint": data["hint"]}
            for num, data in LINK_KNOWLEDGE.items()
        },
    }


# ---------------------------------------------------------------------------
# Internal finding builders
# ---------------------------------------------------------------------------


def _log_provenance(
    *,
    raw_line: str,
    rule: str,
    source: str,
    note: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "rule": rule,
        "source": source,
        "matcher": "regex",
    }
    if raw_line:
        payload["raw_line"] = raw_line[:200]
    if note:
        payload["note"] = note
    return payload


def _scf_convergence_finding(
    *,
    lineno: int,
    raw_line: str,
    last_scf_done: dict[str, Any] | None,
    path: str,
) -> dict[str, Any]:
    facts: dict[str, Any] = {"raw_line": raw_line[:200]}
    if last_scf_done:
        facts["last_method"] = last_scf_done["method"]
        facts["last_cycles"] = last_scf_done["cycles"]
        facts["last_energy"] = last_scf_done["energy"]
    return LogFinding(
        code=CODE_SCF_NOT_CONVERGED,
        severity="error",
        message=(
            "SCF failed to converge within the cycle limit -- the run was " "aborted by Link 502"
        ),
        line=lineno,
        category="preflight/runtime-risk",
        confidence=0.95,
        blocking=True,
        artifact_roles=("runtime-output", "control"),
        facts=facts,
        fix_hints=[
            "Add scf=(xqc, maxcycle=128) to switch to quadratic-convergent SCF",
            "Improve the initial guess with guess=read (after a HF guess run)",
            "Increase the integration grid with int=(ultrafine, acc2e=12)",
        ],
        actions=[
            {
                "kind": "set_route_keyword",
                "value": "scf=(xqc, maxcycle=128)",
                "target": path,
                "safe_to_auto_apply": False,
                "refusal_reason": (
                    "Auto-applying a new SCF strategy may mask a deeper "
                    "electronic-structure issue; require user review."
                ),
            }
        ],
        source_provenance=_log_provenance(
            raw_line=raw_line,
            rule=CODE_SCF_NOT_CONVERGED,
            source="raw/assets/gaussian-output-format.md + cclib gaussianparser",
            note=(
                "Gaussian emits 'Convergence failure' from L502 when the DIIS "
                "queue is exhausted; the SCF Done line above carries the "
                "iteration count."
            ),
        ),
        manual_ref="https://gaussian.com/scf/",
        refusal_reason=("SCF convergence failure requires manual SCF-strategy diagnosis."),
    ).to_dict(path=path)


def _geometry_error_finding(lineno: int, raw_line: str, *, path: str) -> dict[str, Any]:
    return LogFinding(
        code=CODE_GEOMETRY_PARSE_FAILURE,
        severity="error",
        message=(
            "Gaussian reported a geometry / Z-matrix / input parse error in "
            "L101/L402 -- the molecule spec was rejected"
        ),
        line=lineno,
        category="syntax",
        confidence=0.9,
        blocking=True,
        artifact_roles=("runtime-output", "structure"),
        facts={"raw_line": raw_line[:200]},
        fix_hints=[
            "Verify the charge/multiplicity line matches the atom list",
            "Check Z-matrix variable definitions and references",
            "Switch to cartesian input to isolate the Z-matrix parser",
        ],
        actions=[
            {
                "kind": "manual_review",
                "target": path,
                "line": lineno,
                "safe_to_auto_apply": False,
                "refusal_reason": (
                    "Cannot auto-repair: the geometry parser only reports the "
                    "symptom, not which atom/variable caused it."
                ),
            }
        ],
        source_provenance=_log_provenance(
            raw_line=raw_line,
            rule=CODE_GEOMETRY_PARSE_FAILURE,
            source="raw/assets/gaussian-output-format.md",
            note=(
                "L101/L402 emit 'Error in geometry' / 'Input Error' / 'Stop "
                "in parsing' before the supervisor Error termination."
            ),
        ),
        manual_ref="https://gaussian.com/overlay1/#L101",
        refusal_reason="Geometry parse failures require manual input review.",
    ).to_dict(path=path)


def _link_finding(
    *,
    lineno: int,
    raw_line: str,
    link_num: int,
    link_path: str,
    supervisor: str,
    role: str,
    cause: str,
    hint: str,
    path: str,
) -> dict[str, Any]:
    return LogFinding(
        code=CODE_LINK_FAULT,
        severity="error",
        message=(f"Link l{link_num} ({role}) reported a fatal fault -- {cause}"),
        line=lineno,
        category="preflight/runtime-risk",
        confidence=0.95,
        blocking=True,
        artifact_roles=("runtime-output", "control"),
        facts={
            "link_number": link_num,
            "link_executable": link_path,
            "link_role": role,
            "supervisor": supervisor,
            "raw_line": raw_line[:200],
        },
        fix_hints=[
            hint,
            "Search the log above the Error termination line for the "
            "immediate cause emitted by l{0}".format(link_num),
        ],
        actions=[
            {
                "kind": "open_log_context",
                "target": path,
                "line": lineno,
                "safe_to_auto_apply": False,
                "refusal_reason": (
                    f"Link l{link_num} faults require manual log inspection; "
                    "no safe automated repair."
                ),
            }
        ],
        source_provenance=_log_provenance(
            raw_line=raw_line,
            rule=CODE_LINK_FAULT,
            source="raw/assets/gaussian-output-format.md",
            note=(
                "Gaussian links are sequentially numbered executables; the "
                "supervisor line names the failing link so consumers can "
                "narrow the cause."
            ),
        ),
        manual_ref="https://gaussian.com/overlay1/",
        refusal_reason=(
            f"Link l{link_num} faults are non-deterministic; manual review " "required."
        ),
    ).to_dict(path=path)


def _opt_stopped_finding(
    lineno: int,
    raw_line: str,
    nstep: int | None,
    *,
    path: str,
) -> dict[str, Any]:
    facts: dict[str, Any] = {"raw_line": raw_line[:200]}
    if nstep is not None:
        facts["nstep"] = nstep
    return LogFinding(
        code=CODE_OPT_NOT_CONVERGED,
        severity="error",
        message=(
            "Geometry optimization exhausted the step budget without "
            "converging -- Gaussian aborted the optimization"
        ),
        line=lineno,
        category="preflight/runtime-risk",
        confidence=0.9,
        blocking=True,
        artifact_roles=("runtime-output", "optimization"),
        facts=facts,
        fix_hints=[
            "Increase opt=MaxCycle=200 (or higher) and restart from the last "
            "geometry in the log",
            "Recompute the initial Hessian with opt=calcfc for difficult "
            "potential-energy surfaces",
            "Switch to opt=calcfc, recalcfc=20 to refresh the Hessian " "periodically",
        ],
        actions=[
            {
                "kind": "set_route_keyword",
                "value": "opt=(maxcycle=200, calcfc)",
                "target": path,
                "safe_to_auto_apply": False,
                "refusal_reason": (
                    "Auto-extending MaxCycle may hide a chemistry problem "
                    "(flat PES, wrong electronic state); require user review."
                ),
            }
        ],
        source_provenance=_log_provenance(
            raw_line=raw_line,
            rule=CODE_OPT_NOT_CONVERGED,
            source="raw/assets/gaussian-output-format.md",
            note=(
                "L103 emits 'Optimization stopped. -- Number of steps "
                "exceeded, NStep=N' when the Berny optimization runs out of "
                "iterations."
            ),
        ),
        manual_ref="https://gaussian.com/opt/",
        refusal_reason=("Optimization exhaustion requires manual chemistry review."),
    ).to_dict(path=path)


def _memory_exhausted_finding(lineno: int, raw_line: str, *, path: str) -> dict[str, Any]:
    return LogFinding(
        code=CODE_MEMORY_EXHAUSTED,
        severity="error",
        message=(
            "Gaussian ran out of memory/disk during the run -- the runtime "
            "aborted with an allocation error"
        ),
        line=lineno,
        category="preflight/runtime-risk",
        confidence=0.95,
        blocking=True,
        artifact_roles=("runtime-output", "link0"),
        facts={"raw_line": raw_line[:200]},
        fix_hints=[
            "Raise %mem to at least 4GB and confirm the host has enough RAM",
            "For correlated methods, set %mem proportional to N^4 basis size",
            "Switch to the direct/scf=(direct) algorithm to trade CPU for "
            "memory if RAM is constrained",
        ],
        actions=[
            {
                "kind": "set_link0",
                "value": "%mem=4GB",
                "target": path,
                "safe_to_auto_apply": False,
                "refusal_reason": (
                    "Auto-raising memory without knowing the host capacity "
                    "may cause OOM kills; require user review."
                ),
            }
        ],
        source_provenance=_log_provenance(
            raw_line=raw_line,
            rule=CODE_MEMORY_EXHAUSTED,
            source="raw/assets/gaussian-output-format.md",
            note=(
                "Gaussian emits 'Not enough memory' / 'Wanted X bytes of mem' "
                "from the allocation wrapper before the supervisor Error "
                "termination."
            ),
        ),
        manual_ref="https://gaussian.com/techsup/#mem",
        refusal_reason=("Memory fixes require knowing the host's actual RAM budget."),
    ).to_dict(path=path)


def _opt_step_unconverged_finding(lineno: int, raw_line: str, *, path: str) -> dict[str, Any]:
    return LogFinding(
        code=CODE_OPT_STEP_UNCONVERGED,
        severity="warning",
        message=(
            "Optimization convergence criterion not yet met -- this iteration "
            "reported NO on at least one threshold"
        ),
        line=lineno,
        category="semantic consistency",
        confidence=0.8,
        blocking=False,
        artifact_roles=("runtime-output", "optimization"),
        facts={"raw_line": raw_line[:200]},
        fix_hints=[
            "This is normal mid-optimization; only flag as error if the run "
            "ends without 'Optimization completed'",
            "Verify the optimization eventually converges by scanning the "
            "log for the final 'Optimization completed' marker",
        ],
        actions=[
            {
                "kind": "open_log_context",
                "target": path,
                "line": lineno,
                "safe_to_auto_apply": False,
                "refusal_reason": (
                    "Mid-optimization warnings cannot be auto-fixed without "
                    "knowing whether the run eventually converged."
                ),
            }
        ],
        source_provenance=_log_provenance(
            raw_line=raw_line,
            rule=CODE_OPT_STEP_UNCONVERGED,
            source="raw/assets/gaussian-output-format.md",
            note=(
                "L103 emits 'Item ... Value Threshold Converged? NO' lines "
                "during every unconverged optimization step; these are "
                "non-fatal unless the run ends without 'Optimization "
                "completed'."
            ),
        ),
        manual_ref="https://gaussian.com/opt/",
    ).to_dict(path=path)


# ---------------------------------------------------------------------------
# File-level helpers used by the agent CLI
# ---------------------------------------------------------------------------


def is_gaussian_log(path: Path) -> bool:
    """Detect whether a path looks like a Gaussian runtime log.

    The detection is intentionally conservative: Gaussian logs almost always
    contain an ``Entering Gaussian System`` header or a ``Gaussian 16:`` banner
    OR contain one of the well-known termination markers. We require both a
    Gaussian marker AND the .log/.out extension to avoid false positives on
    arbitrary text files.
    """
    suffix = path.suffix.lower()
    if suffix not in {".log", ".out"}:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return _has_gaussian_log_marker(text)


def _has_gaussian_log_marker(text: str) -> bool:
    for marker in (
        "Entering Gaussian System",
        "Gaussian 16:",
        "Gaussian 09:",
        "Normal termination",
        "Error termination",
        "SCF Done:",
    ):
        if marker in text:
            return True
    return False


__all__ = [
    "ALL_LOG_CODES",
    "CODE_ERROR_TERMINATION",
    "CODE_GEOMETRY_PARSE_FAILURE",
    "CODE_LINK_FAULT",
    "CODE_MEMORY_EXHAUSTED",
    "CODE_OPT_NOT_CONVERGED",
    "CODE_OPT_STEP_UNCONVERGED",
    "CODE_SCF_NOT_CONVERGED",
    "LINK_KNOWLEDGE",
    "LogFinding",
    "is_gaussian_log",
    "log_manifest",
    "parse_log",
]
