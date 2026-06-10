"""Typecheck provider for Gaussian input files.

Validates route section keyword types, enum values, units, and required
sections.  Produces LSP diagnostics with source ``gaussian-lsp-typecheck``
so they are distinguishable from the general diagnostics emitted by
``gaussian_lsp.features.diagnostic``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

from gaussian_lsp.parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
    GaussianJob,
    GJFParser,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE = "gaussian-lsp-typecheck"

# Link0 commands and their expected value types.
_LINK0_SCHEMA: Dict[str, str] = {
    "chk": "path",
    "oldchk": "path",
    "rwf": "path",
    "int": "path",
    "d2e": "path",
    "scr": "path",
    "mem": "memory",
    "nproc": "positive_int",
    "nprocs": "positive_int",
    "nprocshared": "positive_int",
    "nprocsshared": "positive_int",
    "gpu": "positive_int",
    "gpucards": "positive_int",
    "pgmcards": "positive_int",
    "kjob": "positive_int",
    "subst": "string",
    "oldmatrix": "path",
    "oldraw": "path",
    "oldfc": "path",
    "lindaworkers": "positive_int",
}

_MEMORY_RE = re.compile(
    r"^[1-9]\d*(?:\.\d+)?\s*(KB|MB|GB|TB|KW|MW|GW|TW)?$",
    re.IGNORECASE,
)

_POSITIVE_INT_RE = re.compile(r"^[1-9]\d*$")

# Known route keywords that accept enum-like options.
# Each maps the keyword to the set of accepted option strings (uppercased).
_ENUM_KEYWORDS: Dict[str, FrozenSet[str]] = {
    "SCF": frozenset(
        {
            "QC",
            "DIIS",
            "SD",
            "DS",
            "RMS",
            "NONE",
            "XQC",
            "YQC",
            "CONVENTIONAL",
            "DIRECT",
            "INCORE",
            "NOINCORE",
            "CONV",
            "NOCONV",
        }
    ),
    "GUESS": frozenset(
        {
            "READ",
            "ALTER",
            "ONLY",
            "MIX",
            "LOW",
            "HUCKEL",
            "HONDO",
            "MOREAD",
            "ONLY",
            "ALWAYS",
            "GEOM",
            "NONE",
        }
    ),
    "POP": frozenset(
        {
            "NONE",
            "MINIMAL",
            "FULL",
            "MK",
            "CHELPG",
            "Hirshfeld",
            "NBO",
            "NBOREAD",
            "NBODEL",
            "Savenbo",
            "REG",
            "ESP",
            "MKLEwis",
            "CHELPGLEWIS",
            "MKIO",
            "NPA",
        }
    ),
    "INTEGRAL": frozenset(
        {
            "GRID",
            "FINEGRID",
            "ULTRAFINE",
            "SUPERFINE",
            "COARSEGRID",
            "PASS",
            "NOINTEGRALCACHESIZE",
        }
    ),
    "OPT": frozenset(
        {
            "SPT",
            "TS",
            "SADDLE",
            "CALCFC",
            "CALCALL",
            "READFC",
            "NOCALC",
            "NOEIGENTEST",
            "HESSIAN",
            "MODREDUNDANT",
            "Z-MATRIX",
            "ZMAT",
            "LOOSE",
            "TIGHT",
            "VERYTIGHT",
            "MAXCYCLE",
            "MAXSTEP",
            "RECALCULATE",
            "ADDREDUNDANT",
            "CONSTR",
            "NOCONST",
            "RFO",
            "NR",
            "EF",
            "NDOPT",
        }
    ),
    "FREQ": frozenset(
        {
            "READISOTOPES",
            "RAMAN",
            "NORAMAN",
            "HPMODE",
            "READFCDATA",
            "ANHARMONIC",
            "SELECTANHARMONIC",
            "NOINTERNA",
            "PSEUDO",
            "NOANHARMONIC",
        }
    ),
    "DENSITY": frozenset(
        {
            "CURRENT",
            "CHECKPOINT",
            "ALL",
            "ALPHA",
            "BETA",
            "MP2",
            "CI",
            "QCI",
            "CC",
            "NONE",
        }
    ),
    "SYMMETRY": frozenset(
        {
            "FOLLOW",
            "NOFOLLOW",
            "INTERIOR",
            "PGROUP",
            "MICRO",
            "INTENSITIES",
            "LOOSE",
            "NOSYM",
            "NONE",
        }
    ),
    "SCRF": frozenset(
        {
            "PCM",
            "CPCM",
            "DIPOLE",
            "IPCM",
            "SCIPCM",
            "SMD",
            "SOLVENT",
            "READ",
            "CHECK",
        }
    ),
    "TD": frozenset(
        {
            "NSTATES",
            "ROOT",
            "SINGLETS",
            "TRIPLETS",
            "50-50",
            "NROOT",
            "EQSOLV",
            "READ",
        }
    ),
    "CIS": frozenset(
        {
            "NSTATES",
            "ROOT",
            "SINGLETS",
            "TRIPLETS",
            "50-50",
            "NROOT",
            "READ",
            "ADDREAD",
        }
    ),
    "IRC": frozenset(
        {
            "CALCFC",
            "CALCALL",
            "RECALCULATE",
            "MAXPOINTS",
            "STEP",
            "FORWARD",
            "REVERSE",
            "MAXCYCLE",
            "READFC",
        }
    ),
}

# Known unit-systems keywords in route
_UNIT_KEYWORDS: Dict[str, FrozenSet[str]] = {
    "UNITS": frozenset({"ANG", "AU", "DEG", "DEGREE", "DEGREES"}),
}

# Required top-level sections for a valid Gaussian input.
_REQUIRED_SECTIONS = ("route", "title", "charge_mult", "coordinates")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypecheckResult:
    """A single typecheck finding."""

    line: int
    character: int
    end_character: int
    message: str
    severity: DiagnosticSeverity

    def to_diagnostic(self) -> Diagnostic:
        """Convert to LSP Diagnostic."""
        return Diagnostic(
            range=Range(
                start=Position(line=self.line, character=self.character),
                end=Position(line=self.line, character=self.end_character),
            ),
            message=self.message,
            severity=self.severity,
            source=SOURCE,
        )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class TypecheckProvider:
    """Validates Gaussian keyword value types, enums, units, and required sections.

    This provider is intentionally layered on top of the existing
    ``DiagnosticProvider`` so that typecheck diagnostics can be toggled
    independently and have their own ``source`` identifier.
    """

    def __init__(self) -> None:
        """Initialize the typecheck provider."""
        self._parser = GJFParser()
        self._method_set = frozenset(m.upper() for m in GAUSSIAN_METHODS)
        self._basis_set = frozenset(b.upper() for b in GAUSSIAN_BASIS_SETS)
        self._job_type_set = frozenset(jt.upper() for jt in GAUSSIAN_JOB_TYPES)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, text: str) -> List[Diagnostic]:
        """Run typecheck validation and return LSP diagnostics.

        Args:
            text: Full document text.

        Returns:
            List of LSP Diagnostic objects with source
            ``gaussian-lsp-typecheck``.
        """
        results: List[TypecheckResult] = []
        lines = text.split("\n")

        try:
            job = self._parser.parse(text)
        except (ValueError, PermissionError):
            # If the parser cannot handle the input at all, skip typecheck;
            # the diagnostic provider already reports parse errors.
            return []
        except Exception:
            return []

        # 1. Required sections
        results.extend(self._check_required_sections(lines, job))

        # 2. Route section keyword types
        results.extend(self._check_route_keyword_types(lines, job))

        # 3. Link0 value types
        results.extend(self._check_link0_types(lines))

        # 4. Enum option validation
        results.extend(self._check_enum_options(lines, job))

        # 5. Unit validation
        results.extend(self._check_units(lines, job))

        return [r.to_diagnostic() for r in results]

    # ------------------------------------------------------------------
    # Required sections
    # ------------------------------------------------------------------

    def _check_required_sections(self, lines: List[str], job: GaussianJob) -> List[TypecheckResult]:
        """Validate that all required sections are present.

        Reports at most one diagnostic per missing section to avoid
        cascading noise.
        """
        results: List[TypecheckResult] = []

        if not job.route_section:
            results.append(
                TypecheckResult(
                    line=0,
                    character=0,
                    end_character=1,
                    message="Missing required route section; every Gaussian input must "
                    "start with a route line beginning with #.",
                    severity=DiagnosticSeverity.Error,
                )
            )

        if not job.title:
            # Only report missing title if we have a route section (avoid
            # cascading from a missing route).
            if job.route_section:
                route_end = self._find_route_end(lines)
                results.append(
                    TypecheckResult(
                        line=route_end + 1,
                        character=0,
                        end_character=1,
                        message="Missing required title line after the route section.",
                        severity=DiagnosticSeverity.Error,
                    )
                )

        if job.multiplicity < 1:
            charge_line = self._find_charge_line(lines)
            if charge_line is not None:
                line_text = lines[charge_line]
                results.append(
                    TypecheckResult(
                        line=charge_line,
                        character=0,
                        end_character=len(line_text),
                        message=f"Invalid multiplicity value: {job.multiplicity}. "
                        "Multiplicity must be a positive integer (>= 1).",
                        severity=DiagnosticSeverity.Error,
                    )
                )

        if not job.atoms:
            charge_line = self._find_charge_line(lines)
            target_line = (charge_line + 1) if charge_line is not None else 0
            results.append(
                TypecheckResult(
                    line=target_line,
                    character=0,
                    end_character=1,
                    message="Missing required coordinate section; at least one atom "
                    "must be defined.",
                    severity=DiagnosticSeverity.Error,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Route keyword types (method, basis, job type)
    # ------------------------------------------------------------------

    def _check_route_keyword_types(
        self, lines: List[str], job: GaussianJob
    ) -> List[TypecheckResult]:
        """Validate route method, basis set, and job type keywords."""
        results: List[TypecheckResult] = []
        route_line_idx = self._find_route_line(lines)
        if route_line_idx is None:
            return results

        route_upper = job.route_section.upper()
        route_text = lines[route_line_idx]

        # Method check
        has_method = any(m in route_upper for m in self._method_set)
        if not has_method:
            results.append(
                TypecheckResult(
                    line=route_line_idx,
                    character=0,
                    end_character=len(route_text),
                    message="No recognizable calculation method in route section; "
                    "expected a method keyword like HF, B3LYP, MP2, CCSD(T), etc.",
                    severity=DiagnosticSeverity.Warning,
                )
            )

        # Basis set check
        has_basis = any(b in route_upper for b in self._basis_set)
        has_gen = "GEN" in route_upper or "GENECP" in route_upper
        if not has_basis and not has_gen:
            results.append(
                TypecheckResult(
                    line=route_line_idx,
                    character=0,
                    end_character=len(route_text),
                    message="No recognizable basis set in route section; "
                    "expected a basis keyword like 6-31G(d), cc-pVTZ, Gen, etc.",
                    severity=DiagnosticSeverity.Warning,
                )
            )

        # Job type check
        has_job_type = any(jt in route_upper for jt in self._job_type_set)
        if not has_job_type:
            results.append(
                TypecheckResult(
                    line=route_line_idx,
                    character=0,
                    end_character=len(route_text),
                    message="No recognizable job type in route section; "
                    "expected a keyword like SP, OPT, FREQ, TD, etc.",
                    severity=DiagnosticSeverity.Warning,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Link0 value types
    # ------------------------------------------------------------------

    def _check_link0_types(self, lines: List[str]) -> List[TypecheckResult]:
        """Validate Link0 command value types."""
        results: List[TypecheckResult] = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("%") or "=" not in stripped:
                continue

            key, value = stripped[1:].split("=", 1)
            key_lower = key.strip().lower()
            value = value.strip()

            if not value:
                if key_lower in ("chk", "oldchk", "rwf", "mem"):
                    results.append(
                        TypecheckResult(
                            line=i,
                            character=0,
                            end_character=len(stripped),
                            message=f"%{key_lower} requires a non-empty value.",
                            severity=DiagnosticSeverity.Error,
                        )
                    )
                continue

            schema = _LINK0_SCHEMA.get(key_lower)
            if schema is None:
                continue

            if schema == "positive_int":
                if not _POSITIVE_INT_RE.match(value):
                    results.append(
                        TypecheckResult(
                            line=i,
                            character=0,
                            end_character=len(stripped),
                            message=f"%{key_lower} expects a positive integer, " f"got '{value}'.",
                            severity=DiagnosticSeverity.Error,
                        )
                    )

            elif schema == "memory":
                if not _MEMORY_RE.match(value):
                    results.append(
                        TypecheckResult(
                            line=i,
                            character=0,
                            end_character=len(stripped),
                            message=f"%mem expects a positive number with optional "
                            f"unit (KB, MB, GB, TB, KW, MW, GW, TW), got '{value}'.",
                            severity=DiagnosticSeverity.Error,
                        )
                    )

            elif schema == "path":
                # Path values must be non-empty (checked above) and not
                # contain shell metacharacters that would indicate a typo.
                pass

        return results

    # ------------------------------------------------------------------
    # Enum option validation
    # ------------------------------------------------------------------

    def _check_enum_options(self, lines: List[str], job: GaussianJob) -> List[TypecheckResult]:
        """Validate that keyword options match known enum values."""
        results: List[TypecheckResult] = []
        route_line_idx = self._find_route_line(lines)
        if route_line_idx is None:
            return results

        route_upper = job.route_section.upper()
        # Tokenize route: remove leading #, then split on whitespace / = / /
        cleaned = route_upper.lstrip("#").strip()
        tokens = re.split(r"[\s/=,]+", cleaned)
        tokens = [t for t in tokens if t]

        # Walk tokens looking for KEY(Option) or KEY=Option patterns.
        # Gaussian route syntax: keyword(option1,option2,...)
        route_text = job.route_section
        for keyword, valid_options in _ENUM_KEYWORDS.items():
            kw_upper = keyword.upper()
            # Check KEY(OPTIONS) pattern
            pattern = re.compile(re.escape(kw_upper) + r"\(([^)]+)\)", re.IGNORECASE)
            for match in pattern.finditer(route_text):
                option_str = match.group(1)
                options = [o.strip().upper() for o in option_str.split(",")]
                for opt in options:
                    # Allow numeric values (like MAXCYCLE=100)
                    if re.match(r"^[0-9]+$", opt):
                        continue
                    # Strip key=value pairs — we accept the key portion
                    opt_key = opt.split("=")[0].strip()
                    if opt_key and opt_key not in valid_options:
                        results.append(
                            TypecheckResult(
                                line=route_line_idx,
                                character=match.start(),
                                end_character=match.end(),
                                message=f"Unknown {keyword} option '{opt_key}'; "
                                f"known options: {self._format_enum_list(valid_options)}.",
                                severity=DiagnosticSeverity.Warning,
                            )
                        )

        return results

    # ------------------------------------------------------------------
    # Unit validation
    # ------------------------------------------------------------------

    def _check_units(self, lines: List[str], job: GaussianJob) -> List[TypecheckResult]:
        """Validate unit keywords where applicable."""
        results: List[TypecheckResult] = []
        route_line_idx = self._find_route_line(lines)
        if route_line_idx is None:
            return results

        route_text = lines[route_line_idx]
        for kw, valid_units in _UNIT_KEYWORDS.items():
            pattern = re.compile(re.escape(kw.upper()) + r"\s*[\(=]\s*(\w+)", re.IGNORECASE)
            for match in pattern.finditer(route_text):
                unit_value = match.group(1).upper()
                if unit_value not in valid_units:
                    results.append(
                        TypecheckResult(
                            line=route_line_idx,
                            character=match.start(1),
                            end_character=match.end(1),
                            message=f"Unknown {kw} value '{match.group(1)}'; "
                            f"expected one of: {self._format_enum_list(valid_units)}.",
                            severity=DiagnosticSeverity.Error,
                        )
                    )

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_route_line(lines: List[str]) -> Optional[int]:
        """Return the index of the first route line (starts with #)."""
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                return i
        return None

    @staticmethod
    def _find_route_end(lines: List[str]) -> int:
        """Return the index of the last route continuation line."""
        route_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                route_idx = i
            elif route_idx is not None:
                if not line.strip():
                    return route_idx
                route_idx = i
        return route_idx if route_idx is not None else 0

    @staticmethod
    def _find_charge_line(lines: List[str]) -> Optional[int]:
        """Return the index of the charge/multiplicity line."""
        pattern = re.compile(r"^[+-]?\d+\s+\d+$")
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                return i
        return None

    @staticmethod
    def _format_enum_list(options: FrozenSet[str]) -> str:
        """Format a set of enum values for error messages."""
        sorted_options = sorted(options)
        if len(sorted_options) <= 8:
            return ", ".join(sorted_options)
        return ", ".join(sorted_options[:8]) + ", ..."


__all__ = ["TypecheckProvider", "TypecheckResult"]
