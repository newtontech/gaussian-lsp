"""Schema-aware static lint checks for Gaussian input files.

Provides :class:`LintProvider` which inspects parsed Gaussian input for
route-keyword validity, section structure, configuration conflicts, and
best-practice smells.  Each finding is returned as an LSP ``Diagnostic``
with a stable ``code`` string (e.g. ``"G001"``) so that automated tools
can filter or suppress rules.

Rule code namespace
~~~~~~~~~~~~~~~~~~

- **G0xx** -- route-section schema violations
- **G1xx** -- Link0 / section-structure checks
- **G2xx** -- chemistry / configuration warnings
- **G3xx** -- best-practice hints
"""

from __future__ import annotations

import re
from typing import Any

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from pygls.server import LanguageServer

from gaussian_lsp.parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
    LINK0_COMMANDS,
    GaussianJob,
    GJFParser,
)

# ------------------------------------------------------------------
# Rule codes
# ------------------------------------------------------------------

#: Route keyword not found in any known keyword list.
RULE_UNKNOWN_ROUTE_KEYWORD = "G001"

#: Route keyword recognised but appears to be a misspelling of a known one.
RULE_ROUTE_TYPO = "G002"

#: Link0 command not in the known command list.
RULE_UNKNOWN_LINK0 = "G010"

#: %nproc value is suspiciously low (1) or very high.
RULE_NPROC_UNUSUAL = "G011"

#: %mem value is suspiciously low (< 128 MB) for typical jobs.
RULE_MEM_LOW = "G012"

#: Job type keyword missing from route.
RULE_NO_JOB_TYPE = "G020"

#: FREQ without OPT may be unintended for geometry verification.
RULE_FREQ_WITHOUT_OPT = "G021"

#: OPT with loose convergence criteria may give unreliable geometries.
RULE_OPT_LOOSE_CONVERGENCE = "G022"

#: Multiplicity > 1 but no UHF/ROHF specified for DFT/HF.
RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED = "G030"

#: SCF convergence criteria too loose for post-HF methods.
RULE_SCF_CONVERGENCE_POSTHF = "G031"

#: Route verbosity level is missing or overly terse.
RULE_VERBOSITY_HINT = "G040"

# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

_ROUTE_SPLIT = re.compile(r"[\s/,=]+")

# Known route-level keywords that are not methods, basis sets, or job types.
_EXTRA_ROUTE_KEYWORDS: frozenset[str] = frozenset(
    {
        # SCF options
        "SCF",
        "CONVENTIONAL",
        "DIRECT",
        "INCORE",
        # Guess
        "GUESS",
        "READ",
        "MIX",
        "ONLY",
        "ALTER",
        "HUCKEL",
        "CARD",
        # Integral
        "INTEGRALS",
        "GRID",
        "FINE",
        "ULTRAFINE",
        "SG1",
        "COARSE",
        # Opt options
        "MAXCYCLE",
        "LOPT",
        "NOLOG",
        "READFC",
        "FC",
        "SADDLE",
        "CALCFC",
        "CALCALL",
        "NOGRADIENT",
        "HESSIAN",
        "MODREDUNDANT",
        "MODREDBND",
        "NOMRED",
        # General
        "POP",
        "DENSITY",
        "OUTPUT",
        "IOp",
        "SYMMETRY",
        "NOSYMM",
        "NOINTERACTION",
        "TEST",
        "CHK",
        "RWFD",
        "SCFCON",
        "SCFDM",
        "SCFQC",
        "DIIS",
        "VDW",
        "VOLUME",
        "SYMM",
        "LOOSE",
        "TIGHT",
        "VERYTIGHT",
        "NOSYM",
        "NO.SYMMETRY",
        "GEOM",
        "ALLCHECK",
        "CHECK",
        "FORMCHECK",
        "OLDPHASE",
        "TRANSITION",
        "NOINTERNA",
        # Opt/Freq qualifiers
        "Z-MATRIX",
        "CARTESIAN",
        "REDUNDANT",
        "INTERNAL",
        "NORAMAN",
        "NOANHARMONIC",
        "ANHARMONIC",
        "READISOTOPES",
        "SAVE",
        "NOSAVE",
        "TEMPERATURE",
        "PRESSURE",
        "SCALE",
        # Pop options
        "FULL",
        "MK",
        "CHELPG",
        "HIRSHFELD",
        "NBO",
        "NBOREAD",
        "NPA",
        "MULLIKEN",
        "ESP",
        "CHARGES",
        # Integral / SCF options
        "SUPERFINE",
        "FINEGRID",
        "COARSEGRID",
        # CD, CIS, TD options
        "SINGLETS",
        "TRIPLETS",
        "ROOT",
        "NSTATES",
        "EQUILIBRIA",
        "TRUST",
        "MAXSTEP",
        "RECALCULE",
        "LINESEARCH",
        "TIGHTCONVERGENCE",
        "VERYTIGHTCONVERGENCE",
        "REOPTIMIZED",
        # Restart / checkpoint
        "READMO",
        "SAVEFC",
        "RDCHECK",
        "WRTCHECK",
        "ALL",
        "NONE",
        "MINIMAL",
        "NORMAL",
        # Basis / route
        "GEN",
        "GENECP",
        "CHKBASIS",
        "EXTRABASIS",
        "DIFFUSE",
        "POLARIZATION",
        # Solvation
        "SCRF",
        "PCM",
        "SMD",
        "DIELECTRIC",
        "SOLVENT",
        # Misc
        "MOLECULE",
        "MO",
        "PRINT",
        "NOPRINT",
    }
)

# All valid route tokens (methods + basis + job types + extras), upper-cased.
_ALL_VALID_TOKENS: frozenset[str] = (
    frozenset(kw.upper() for kw in GAUSSIAN_METHODS)
    | frozenset(kw.upper() for kw in GAUSSIAN_BASIS_SETS)
    | frozenset(kw.upper() for kw in GAUSSIAN_JOB_TYPES)
    | frozenset(kw.upper() for kw in _EXTRA_ROUTE_KEYWORDS)
    | {"#", "P", "T", "N"}
)

# Common misspelling map (misspelling -> suggestion).
_TYPO_MAP: dict[str, str] = {
    "FREQENCY": "FREQ",
    "OPTIMIZE": "OPT",
    "FREQUENCY": "FREQ",
    "BA3LYP": "B3LYP",
    "B3LY": "B3LYP",
    "M06-2X": "M062X",
    "631G": "6-31G",
    "6311G": "6-311G",
    "OPTIMISE": "OPT",
    "HARTREEFOCK": "HF",
}


def _severity_name(severity: int | None) -> str:
    """Map numeric severity to a stable string label."""
    mapping = {
        DiagnosticSeverity.Error: "error",
        DiagnosticSeverity.Warning: "warning",
        DiagnosticSeverity.Information: "information",
        DiagnosticSeverity.Hint: "hint",
    }
    if severity is None:
        return "error"
    return mapping.get(severity, "error")


class LintProvider:
    """Schema-aware static lint rules for Gaussian input files.

    Returns findings as LSP ``Diagnostic`` objects with ``source`` set to
    ``"gaussian-lsp-lint"`` and stable ``code`` values from the ``G0xx``
    namespace.

    Parameters
    ----------
    server:
        The language server instance (kept for symmetry with
        :class:`DiagnosticProvider`; not queried at runtime).
    """

    SOURCE = "gaussian-lsp-lint"

    def __init__(self, server: LanguageServer) -> None:
        self.server = server

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lint(self, text: str) -> list[Diagnostic]:
        """Run all lint rules and return diagnostics.

        Args:
            text: Full document text.

        Returns:
            List of LSP Diagnostic objects with ``source`` set to
            ``gaussian-lsp-lint``.
        """
        diagnostics: list[Diagnostic] = []
        parser = GJFParser()

        try:
            job = parser.parse(text)
        except Exception:
            # If parsing fails, the DiagnosticProvider already reports it.
            return diagnostics

        lines = text.split("\n")
        route_line = self._find_route_line(lines)

        self._check_route_keywords(lines, route_line, job, diagnostics)
        self._check_link0_commands(lines, job, diagnostics)
        self._check_job_type_rules(lines, route_line, job, diagnostics)
        self._check_open_shell(lines, route_line, job, diagnostics)
        self._check_scf_convergence(lines, route_line, job, diagnostics)
        self._check_verbosity_hint(lines, route_line, diagnostics)

        return diagnostics

    def snapshot(self, text: str) -> list[dict[str, Any]]:
        """Return a JSON-serializable snapshot of lint findings.

        Each entry has keys ``range``, ``severity``, ``source``,
        ``message``, and ``code``.  The result is deterministically
        ordered by ``(line, character, severity_rank)``.

        Args:
            text: Full document text.

        Returns:
            A list of plain dicts suitable for ``json.dumps``.
        """
        diagnostics = self.lint(text)
        return self._serialize(diagnostics)

    # ------------------------------------------------------------------
    # Route-section checks (G0xx)
    # ------------------------------------------------------------------

    def _check_route_keywords(
        self,
        lines: list[str],
        route_line: int | None,
        job: GaussianJob,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Validate individual route tokens against the known keyword set."""
        if route_line is None or not job.route_section:
            return

        tokens = self._route_tokens(job.route_section)
        for token in tokens:
            upper = token.upper()
            if upper in _ALL_VALID_TOKENS:
                continue
            # Heuristic: single-letter or very short tokens are usually noise.
            if len(token) <= 1:
                continue
            # Heuristic: pure numeric tokens are IOp parameters or other values.
            if token.isdigit():
                continue

            # Check typo map first.
            matched_typo: str | None = None
            for typo, suggestion in _TYPO_MAP.items():
                if upper == typo:
                    matched_typo = suggestion
                    break

            col = self._token_column(lines[route_line], token)
            end_col = col + len(token)
            range_ = Range(
                start=Position(line=route_line, character=col),
                end=Position(line=route_line, character=end_col),
            )

            if matched_typo is not None:
                diagnostics.append(
                    Diagnostic(
                        range=range_,
                        message=f"Possible typo: '{token}' -- did you mean " f"'{matched_typo}'?",
                        severity=DiagnosticSeverity.Error,
                        source=self.SOURCE,
                        code=RULE_ROUTE_TYPO,
                    )
                )
            else:
                diagnostics.append(
                    Diagnostic(
                        range=range_,
                        message=f"Unknown route keyword: '{token}'",
                        severity=DiagnosticSeverity.Warning,
                        source=self.SOURCE,
                        code=RULE_UNKNOWN_ROUTE_KEYWORD,
                    )
                )

    # ------------------------------------------------------------------
    # Link0 checks (G1xx)
    # ------------------------------------------------------------------

    def _check_link0_commands(
        self,
        lines: list[str],
        job: GaussianJob,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check Link0 commands for unknown keys and unusual values."""
        known_link0 = frozenset(cmd.lower() for cmd in LINK0_COMMANDS)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("%") or "=" not in stripped:
                continue
            key = stripped[1:].split("=", 1)[0].strip().lower()
            if key not in known_link0:
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=i, character=0),
                            end=Position(line=i, character=len(stripped)),
                        ),
                        message=f"Unknown Link0 command: '%{key}'",
                        severity=DiagnosticSeverity.Warning,
                        source=self.SOURCE,
                        code=RULE_UNKNOWN_LINK0,
                    )
                )

            # nproc checks
            if key in {"nproc", "nprocs", "nprocshared", "nprocsshared"}:
                value = stripped.split("=", 1)[1].strip()
                if value.isdigit():
                    n = int(value)
                    if n == 1:
                        diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(line=i, character=0),
                                    end=Position(line=i, character=len(stripped)),
                                ),
                                message="%nproc is set to 1; consider increasing "
                                "for faster parallel computation.",
                                severity=DiagnosticSeverity.Hint,
                                source=self.SOURCE,
                                code=RULE_NPROC_UNUSUAL,
                            )
                        )

            # mem checks
            if key == "mem":
                value = stripped.split("=", 1)[1].strip()
                mb = self._parse_mem_mb(value)
                if mb is not None and mb < 128:
                    diagnostics.append(
                        Diagnostic(
                            range=Range(
                                start=Position(line=i, character=0),
                                end=Position(line=i, character=len(stripped)),
                            ),
                            message=f"%mem is set to {mb} MB; most Gaussian "
                            "jobs benefit from at least 128 MB.",
                            severity=DiagnosticSeverity.Hint,
                            source=self.SOURCE,
                            code=RULE_MEM_LOW,
                        )
                    )

    # ------------------------------------------------------------------
    # Job-type configuration checks (G2xx)
    # ------------------------------------------------------------------

    def _check_job_type_rules(
        self,
        lines: list[str],
        route_line: int | None,
        job: GaussianJob,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check job-type related configuration smells."""
        if route_line is None:
            return

        tokens = set(self._route_tokens(job.route_section))
        route_range = Range(
            start=Position(line=route_line, character=0),
            end=Position(line=route_line, character=len(lines[route_line])),
        )

        # G020: No job type keyword.
        has_job_type = any(jt.upper() in tokens for jt in GAUSSIAN_JOB_TYPES)
        if not has_job_type and "SP" not in tokens:
            diagnostics.append(
                Diagnostic(
                    range=route_range,
                    message="No explicit job type keyword (e.g. OPT, FREQ, SP); "
                    "single-point (SP) is assumed.",
                    severity=DiagnosticSeverity.Information,
                    source=self.SOURCE,
                    code=RULE_NO_JOB_TYPE,
                )
            )

        # G021: FREQ without OPT.
        if "FREQ" in tokens and "OPT" not in tokens:
            diagnostics.append(
                Diagnostic(
                    range=route_range,
                    message="FREQ without OPT -- verify the geometry is already "
                    "optimised, or use OPT FREQ to verify the stationary point.",
                    severity=DiagnosticSeverity.Information,
                    source=self.SOURCE,
                    code=RULE_FREQ_WITHOUT_OPT,
                )
            )

        # G022: OPT with loose convergence.
        if "OPT" in tokens and "LOOSE" in tokens:
            diagnostics.append(
                Diagnostic(
                    range=route_range,
                    message="OPT with LOOSE convergence may give geometries that "
                    "fail frequency verification.",
                    severity=DiagnosticSeverity.Warning,
                    source=self.SOURCE,
                    code=RULE_OPT_LOOSE_CONVERGENCE,
                )
            )

    # ------------------------------------------------------------------
    # Chemistry / configuration checks (G2xx continued)
    # ------------------------------------------------------------------

    def _check_open_shell(
        self,
        lines: list[str],
        route_line: int | None,
        job: GaussianJob,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Warn when multiplicity > 1 but the method is not unrestricted."""
        if route_line is None or job.multiplicity <= 1:
            return

        tokens = set(self._route_tokens(job.route_section))

        has_uhf = "UHF" in tokens
        has_rohf = "ROHF" in tokens
        has_posthf = any(m in tokens for m in ("MP2", "MP3", "MP4", "MP4SDQ", "MP5"))
        has_dft = any(
            m in tokens
            for m in (
                "B3LYP",
                "PBE",
                "PBE0",
                "M06",
                "M062X",
                "M06L",
                "M06HF",
                "WB97",
                "WB97X",
                "WB97XD",
                "CAM-B3LYP",
                "BLYP",
                "BP86",
                "TPSS",
                "TPSSH",
            )
        )
        has_semi = any(m in tokens for m in ("PM3", "PM6", "PM7", "AM1", "RM1", "MNDO", "MNDOD"))

        if has_uhf or has_rohf or has_dft or has_semi:
            return

        route_range = Range(
            start=Position(line=route_line, character=0),
            end=Position(line=route_line, character=len(lines[route_line])),
        )

        # For HF with open shell, warn only if RHF is explicitly used.
        if "HF" in tokens or "RHF" in tokens:
            if "RHF" in tokens:
                diagnostics.append(
                    Diagnostic(
                        range=route_range,
                        message=f"Multiplicity is {job.multiplicity} but RHF is "
                        "specified -- use UHF or ROHF for open-shell systems.",
                        severity=DiagnosticSeverity.Warning,
                        source=self.SOURCE,
                        code=RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED,
                    )
                )

        # For post-HF methods, just hint.
        if has_posthf and not has_uhf:
            diagnostics.append(
                Diagnostic(
                    range=route_range,
                    message=f"Multiplicity is {job.multiplicity} -- verify that "
                    "the post-HF method supports open-shell references.",
                    severity=DiagnosticSeverity.Information,
                    source=self.SOURCE,
                    code=RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED,
                )
            )

    def _check_scf_convergence(
        self,
        lines: list[str],
        route_line: int | None,
        job: GaussianJob,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Warn about loose SCF convergence with post-HF methods."""
        if route_line is None:
            return

        tokens = set(self._route_tokens(job.route_section.upper()))
        has_posthf = any(
            m in tokens for m in ("MP2", "MP3", "MP4", "MP4SDQ", "MP5", "CCSD", "CCSD(T)")
        )
        has_loose_scf = "SCFCON" in tokens or "LOOSE" in tokens

        if has_posthf and has_loose_scf:
            route_range = Range(
                start=Position(line=route_line, character=0),
                end=Position(line=route_line, character=len(lines[route_line])),
            )
            diagnostics.append(
                Diagnostic(
                    range=route_range,
                    message="Post-HF methods require tight SCF convergence; "
                    "avoid loose SCF settings.",
                    severity=DiagnosticSeverity.Warning,
                    source=self.SOURCE,
                    code=RULE_SCF_CONVERGENCE_POSTHF,
                )
            )

    # ------------------------------------------------------------------
    # Best-practice hints (G3xx)
    # ------------------------------------------------------------------

    def _check_verbosity_hint(
        self,
        lines: list[str],
        route_line: int | None,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Hint if route line uses ``#`` (minimal output)."""
        if route_line is None:
            return

        route = lines[route_line].strip()
        # ``#`` alone means minimal output; ``#P`` / ``#N`` / ``#T`` are fine.
        if route == "#" or (route.startswith("#") and len(route) > 1 and route[1] == " "):
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=route_line, character=0),
                        end=Position(line=route_line, character=1),
                    ),
                    message="Route uses minimal output ('#'); consider '#P' for "
                    "more detailed output or '#N' for normal output.",
                    severity=DiagnosticSeverity.Hint,
                    source=self.SOURCE,
                    code=RULE_VERBOSITY_HINT,
                )
            )

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(diagnostics: list[Diagnostic]) -> list[dict[str, Any]]:
        """Convert LSP Diagnostic objects to deterministic dicts."""
        severity_order = {
            "error": 0,
            "warning": 1,
            "information": 2,
            "hint": 3,
        }
        snapshot: list[dict[str, Any]] = []
        for diag in diagnostics:
            sev_name = _severity_name(diag.severity)
            entry: dict[str, Any] = {
                "range": {
                    "start": {
                        "line": diag.range.start.line,
                        "character": diag.range.start.character,
                    },
                    "end": {
                        "line": diag.range.end.line,
                        "character": diag.range.end.character,
                    },
                },
                "severity": sev_name,
                "source": diag.source or LintProvider.SOURCE,
                "message": diag.message,
            }
            if diag.code is not None:
                entry["code"] = str(diag.code)
            snapshot.append(entry)

        snapshot.sort(
            key=lambda d: (
                d["range"]["start"]["line"],
                d["range"]["start"]["character"],
                severity_order.get(d["severity"], 4),
            )
        )
        return snapshot

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _find_route_line(lines: list[str]) -> int | None:
        """Find the first route line (starts with ``#``)."""
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                return i
        return None

    @staticmethod
    def _route_tokens(route_section: str) -> list[str]:
        """Return uppercase Gaussian route tokens."""
        cleaned = route_section.replace("#", " ").replace("(", " ").replace(")", " ")
        return [t.upper() for t in _ROUTE_SPLIT.split(cleaned) if t]

    @staticmethod
    def _token_column(line: str, token: str) -> int:
        """Return the column offset of *token* in *line*, case-insensitive."""
        idx = line.upper().find(token.upper())
        return max(idx, 0)

    @staticmethod
    def _parse_mem_mb(value: str) -> int | None:
        """Parse a Gaussian memory value to megabytes.

        Returns ``None`` if the value cannot be parsed.
        """
        match = re.match(
            r"^([1-9]\d*(?:\.\d+)?)\s*(KB|MB|GB|TB|KW|MW|GW|TW)?$",
            value,
            re.I,
        )
        if not match:
            return None
        amount = float(match.group(1))
        unit = (match.group(2) or "MB").upper()
        multipliers: dict[str, float] = {
            "KB": 1 / 1024,
            "MB": 1,
            "GB": 1024,
            "TB": 1024 * 1024,
            "KW": 8 / 1024,
            "MW": 8,
            "GW": 8 * 1024,
            "TW": 8 * 1024 * 1024,
        }
        return int(amount * multipliers.get(unit, 1))


__all__ = ["LintProvider"]
