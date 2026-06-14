"""Universal generated-input preflight capabilities.

This module implements the four fleet-wide preflight capabilities called out in
``newtontech/gaussian-lsp#76`` against a *generic artifact-role model*, so the
checks generalize to any backend in the scientific LSP fleet instead of being
wired to MatMaster submission policy:

* ``version-aware-keywords``  - explicit runtime/version assumption metadata and
  method/basis compatibility validation derived from the Gaussian keyword
  schema, never guessed.
* ``cross-artifact-graph``   - resolves a Gaussian ``.gjf``/``.com`` input as a
  graph of artifacts with stable generic roles (primary-input, control, basis,
  structure, link0, guess, pseudopotential, optimization, dft). The same model
  works for GAMESS/VASP/ABACUS/GROMACS/etc. because the cross-section checks
  operate on the graph rather than ad-hoc section names.
* ``code-actions``           - normalizes repair hints/actions on every
  diagnostic and exposes a blocking gate the agent CLI can run as
  ``check --fail-on-blocking`` plus a dedicated ``preflight`` subcommand.
* ``fleet-regression-fixtures`` - ``fleet_manifest`` returns a machine-readable
  description of the preflight surface (codes, capabilities, fixture
  expectations) so the parent ``bohrium_skills`` probe/report workflow can
  consume regression evidence without re-deriving it.

Gaussian packs its inputs into a single ``.gjf``/``.com`` file made of a Link0
``%`` block, the ``#`` route card, a title line, and a molecule specification
(charge/multiplicity + atoms). The cross-artifact graph models the *logical*
artifacts (route control deck, basis set, molecule structure, Link0 ancillary,
guess/restart, ECP, optimization, DFT) rather than separate physical files.
The roles are the same generic fleet roles the parent router understands; only
the Gaussian-specific binding (route keyword / section -> role) lives here.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_METHODS,
    GaussianJob,
    GJFParser,
)

# --- Artifact-role model ---------------------------------------------------

# Generic roles. These are intentionally software-agnostic: every fleet backend
# can map its native inputs onto this same small role set, which is what lets
# the parent router consume cross-section/cross-file checks without learning
# MatMaster specifics.
ROLE_PRIMARY_INPUT = "primary-input"
ROLE_CONTROL = "control"
ROLE_BASIS = "basis"
ROLE_STRUCTURE = "structure"
ROLE_LINK0 = "link0"
ROLE_GUESS = "guess"
ROLE_PSEUDOPOTENTIAL = "pseudopotential"
ROLE_OPTIMIZATION = "optimization"
ROLE_DFT = "dft"

ALL_ROLES = (
    ROLE_PRIMARY_INPUT,
    ROLE_CONTROL,
    ROLE_BASIS,
    ROLE_STRUCTURE,
    ROLE_LINK0,
    ROLE_GUESS,
    ROLE_PSEUDOPOTENTIAL,
    ROLE_OPTIMIZATION,
    ROLE_DFT,
)

# Binding from Gaussian sections / route keywords to the generic fleet role.
# A route keyword realizes a role (``gen``/``genecp`` realize the basis role,
# ``pseudo=read`` realizes the pseudopotential role, etc.); the molecule spec
# realizes the structure artifact just like a VASP POSCAR or ABACUS STRU.
SECTION_ROLE_BINDING: dict[str, str] = {
    "route": ROLE_CONTROL,
    "title": ROLE_PRIMARY_INPUT,
    "molecule": ROLE_STRUCTURE,
    "link0": ROLE_LINK0,
    "chk": ROLE_LINK0,
    "mem": ROLE_LINK0,
    "nproc": ROLE_LINK0,
    "oldchk": ROLE_GUESS,
}

# Conservative workflow thresholds used by the warning-level checks. The actual
# cutoffs are overridable via the preflight intent contract; these are only the
# default fleet baselines, not MatMaster policy.
# %mem is parsed as a human-friendly amount (MB/GB). < 256MB is often too small
# for production Gaussian jobs (disk-based integral storage spills easily).
DEFAULT_MEM_WARNING_MB = 256.0
# An OPT route without MaxCycle lets the default driver pick; we only warn when
# the user explicitly set MaxCycle to a suspiciously low value.
DEFAULT_OPT_MAXCYCLE_WARNING_FLOOR = 1
# %nproc=1 is legitimate for tiny jobs but common as a silent mis-configuration
# on HPC nodes; warning-level only.
DEFAULT_NPROC_WARNING = 1

# Codes reserved for the universal preflight surface. They use the ``GAUSSIAN6xx``
# band so they sort after existing rule codes (G0xx/G1xx/G2xx/G3xx) and stay
# identifiable as cross-fleet preflight findings.
CODE_MISSING_ROUTE = "GAUSSIAN601"
CODE_STRUCTURE_EMPTY = "GAUSSIAN602"
CODE_MISSING_BASIS = "GAUSSIAN603"
CODE_GUESS_READ_WITHOUT_OLDCHK = "GAUSSIAN604"
CODE_PSEUDO_WITHOUT_BASIS = "GAUSSIAN605"
CODE_LOW_MEM = "GAUSSIAN606"
CODE_OPT_MAXCYCLE_DISABLED = "GAUSSIAN607"
CODE_VERSION_ASSUMPTION = "GAUSSIAN608"
CODE_METHOD_BASIS_MISMATCH = "GAUSSIAN609"
CODE_DFT_WITHOUT_FUNCTIONAL = "GAUSSIAN610"

# Job-type keywords (in the route card) that drive an optimization and therefore
# make MaxCycle relevant.
_OPT_JOB_KEYWORDS = {"OPT", "POPT"}

# Methods that imply an unrestricted or restricted open-shell reference and so
# pair with a multiplicity > 1. We surface a finding only for the negative case
# (open-shell declared but the route is closed-shell), not the full matrix.
_OPEN_SHELL_METHODS = {"UHF", "UMP2", "UMP3", "UMP4", "UCCSD", "UCCSD(T)", "ROHF", "ROMP2"}

# Methods that are correlated (post-HF) and therefore meaningless on a minimal
# basis. We use the same conservative families the GAMESS preflight uses so the
# fleet probe can apply one rule across backends.
_CORRELATED_METHOD_TOKENS = {"MP2", "MP3", "MP4", "MP5", "CCSD", "QCISD", "BD"}
_MINIMAL_BASIS_TOKENS = {"STO-3G", "3-21G", "STO-3G*", "3-21G*", "STO", "MINI", "MIDI", "LANL2MB"}


@dataclass(frozen=True)
class ArtifactNode:
    """A node in the cross-artifact graph.

    ``role`` is one of the fleet-generic roles above; ``section`` is the
    Gaussian section/keyword that realizes this role (or ``None`` when the role
    is the primary input file itself); ``exists`` records whether the section is
    present in the parsed input; ``source`` records where the binding originated
    so consumers can trace provenance.
    """

    role: str
    section: str | None
    exists: bool
    source: str
    line: int
    detail: dict[str, Any] | None = None


@dataclass
class ArtifactGraph:
    """Generic cross-artifact graph built from a parsed Gaussian input."""

    input_path: Path
    nodes: list[ArtifactNode] = field(default_factory=list)

    def by_role(self, role: str) -> list[ArtifactNode]:
        return [node for node in self.nodes if node.role == role]

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize the graph for the parent probe/report workflow."""

        def _node_json(node: ArtifactNode) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "role": node.role,
                "section": node.section,
                "exists": node.exists,
                "source": node.source,
                "line": node.line,
            }
            if node.detail:
                payload["detail"] = node.detail
            return payload

        return sorted(
            (_node_json(node) for node in self.nodes),
            key=lambda item: (item["role"], item["section"] or "", item["line"]),
        )


def _index_sections(text: str) -> dict[str, int]:
    """Return a 1-based line index for the canonical Gaussian sections.

    We avoid re-parsing here and instead look for the well-known structural
    anchors: the first ``%`` Link0 line, the first ``#`` route line, and the
    charge/multiplicity line that begins the molecule spec. This is enough for
    provenance; the full parse is performed separately by the LSP parser.
    """
    index: dict[str, int] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("!"):
            continue
        if "link0" not in index and stripped.startswith("%"):
            index["link0"] = lineno
        if "route" not in index and stripped.startswith("#"):
            index["route"] = lineno
    return index


def build_artifact_graph(input_path: Path, job: GaussianJob, text: str) -> ArtifactGraph:
    """Build the cross-artifact graph from a parsed Gaussian input.

    The model is generic: it records roles + the Gaussian section that realizes
    each role + provenance. The same shape generalizes to other fleet backends
    because it never bakes in MatMaster/Bohrium runtime concepts (no image, no
    session, no submission policy).
    """
    section_lines = _index_sections(text)
    graph = ArtifactGraph(input_path=input_path.resolve())
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_PRIMARY_INPUT,
            section=None,
            exists=True,
            source="case-root",
            line=1,
        )
    )

    # control = the route card. A Gaussian input without a ``#`` route cannot
    # be submitted at all, so this is the mandatory control deck.
    route_line = section_lines.get("route", 1)
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_CONTROL,
            section="route",
            exists=bool(job.route_section),
            source="# route card",
            line=route_line,
            detail={"route_present": bool(job.route_section)},
        )
    )

    # structure = the molecule specification (charge/multiplicity + atoms).
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_STRUCTURE,
            section="molecule",
            exists=bool(job.atoms),
            source="molecule spec (charge mult + atoms)",
            line=1,
            detail={"atom_count": len(job.atoms)},
        )
    )

    # link0 = the % ancillary block (chk/mem/nproc/oldchk). Optional but
    # common; provenance is the first ``%`` line if present.
    link0_line = section_lines.get("link0", 1)
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_LINK0,
            section="link0",
            exists=bool(job.link0),
            source="% Link0 commands",
            line=link0_line,
            detail={"commands": sorted(job.link0) if job.link0 else []},
        )
    )

    # basis = basis-set keyword in the route, the ``gen``/``genecp`` keyword, or
    # an external ``@file.gbs`` basis file. Resolved later in preflight.
    route_tokens = _route_tokens(job.route_section)
    known_basis_upper = {b.upper() for b in GAUSSIAN_BASIS_SETS}
    has_basis_kw = any(tok.upper() in known_basis_upper for tok in route_tokens)
    has_gen = "GEN" in route_tokens or "GENECP" in route_tokens
    has_external = "@" in job.route_section
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_BASIS,
            section="basis",
            exists=has_basis_kw or has_gen or has_external or job.gen_basis is not None,
            source="route basis keyword / gen / @file",
            line=route_line,
            detail={
                "basis_keyword": has_basis_kw,
                "gen": has_gen,
                "external_file": has_external,
                "inline_gen_basis": job.gen_basis is not None,
            },
        )
    )

    # guess = restart orbitals via ``guess=read`` + ``%oldchk``. Resolved later.
    has_guess_read = "GUESS=READ" in job.route_section.upper()
    has_oldchk = "oldchk" in {k.lower() for k in job.link0}
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_GUESS,
            section="guess",
            exists=has_guess_read or has_oldchk,
            source="guess=read / %oldchk",
            line=link0_line,
            detail={"guess_read": has_guess_read, "oldchk": has_oldchk},
        )
    )

    # pseudopotential = ``pseudo=read`` or ``genecp`` in the route.
    has_pseudo = (
        "PSEUDO=READ" in job.route_section.upper()
        or "PSEUDOREAD" in job.route_section.upper()
        or "GENECP" in route_tokens
    )
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_PSEUDOPOTENTIAL,
            section="pseudo",
            exists=has_pseudo,
            source="pseudo=read / genecp",
            line=route_line,
            detail={"declared": has_pseudo},
        )
    )

    # optimization = ``OPT``/``POPT`` job type keyword in the route.
    has_opt = bool(_OPT_JOB_KEYWORDS & {tok.upper() for tok in route_tokens})
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_OPTIMIZATION,
            section="opt",
            exists=has_opt,
            source="route OPT/POPT job type",
            line=route_line,
            detail={
                "opt_keyword": sorted(_OPT_JOB_KEYWORDS & {tok.upper() for tok in route_tokens})
            },
        )
    )

    # dft = a DFT functional token in the route.
    has_dft_functional = _detect_dft_functional(job.route_section) is not None
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_DFT,
            section="dft",
            exists=has_dft_functional,
            source="route DFT functional token",
            line=route_line,
            detail={"functional": _detect_dft_functional(job.route_section)},
        )
    )

    return graph


# --- Preflight diagnostics -------------------------------------------------


def preflight_diagnostics(
    input_path: Path,
    *,
    intent: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], ArtifactGraph]:
    """Run universal generated-input preflight checks.

    Returns a tuple of (diagnostics, artifact_graph). Diagnostics are envelope
    dicts carrying the full ``DiagnosticEnvelope/v1`` field set so the agent
    CLI can emit them directly without re-shaping.
    """
    input_path = input_path.resolve()
    text = input_path.read_text(encoding="utf-8", errors="ignore")
    parser = GJFParser()
    try:
        job = parser.parse(text)
    except (ValueError, OSError):
        # An unparseable input still produces a minimal graph so the parent
        # probe gets a stable shape; the missing-route diagnostic surfaces the
        # parse failure as a blocking preflight finding.
        job = GaussianJob()
    graph = build_artifact_graph(input_path, job, text)

    version_assumption = resolve_version_assumption(intent)
    diagnostics: list[dict[str, Any]] = []
    diagnostics.extend(_missing_route_diagnostics(graph, job, input_path))
    diagnostics.extend(_structure_diagnostics(graph, job, input_path))
    diagnostics.extend(_basis_diagnostics(graph, job, input_path))
    diagnostics.extend(_guess_oldchk_diagnostics(graph, job, input_path))
    diagnostics.extend(_pseudo_basis_diagnostics(graph, job, input_path))
    diagnostics.extend(_low_mem_diagnostics(graph, job, input_path, intent))
    diagnostics.extend(_opt_maxcycle_diagnostics(graph, job, input_path))
    diagnostics.extend(
        _method_basis_mismatch_diagnostics(graph, job, input_path, version_assumption)
    )
    diagnostics.extend(
        _dft_without_functional_diagnostics(graph, job, input_path, version_assumption)
    )
    diagnostics.extend(_version_assumption_diagnostic(version_assumption, intent, input_path))

    return (
        sorted(
            diagnostics,
            key=lambda item: (
                item.get("range", {}).get("start", {}).get("line", 0),
                item.get("range", {}).get("start", {}).get("character", 0),
                item["code"],
            ),
        ),
        graph,
    )


def _diag(
    *,
    code: str,
    severity: str,
    message: str,
    path: Path,
    line: int = 1,
    column: int = 1,
    category: str,
    confidence: float,
    blocking: bool,
    source_provenance: dict[str, Any],
    fix_hints: list[str],
    actions: list[dict[str, Any]] | None = None,
    facts: dict[str, Any] | None = None,
    artifact_roles: list[str] | None = None,
    domain_tags: list[str] | None = None,
    version_assumption: dict[str, Any] | None = None,
    manual_ref: str | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single normalized preflight diagnostic.

    Carries every field the issue acceptance criteria require (``code``,
    ``severity``, ``path``/``range``, ``blocking``, ``category``,
    ``source_provenance``, ``fix_hints``/``actions``) plus the richer envelope
    fields (``facts``, ``artifact_roles``, ``domain_tags``,
    ``version_assumption``) used by the parent fleet probe.
    """
    line0 = max(line - 1, 0)
    col0 = max(column - 1, 0)
    payload: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "file": str(path),
        "path": str(path),
        "line": line,
        "column": column,
        "category": category,
        "confidence": confidence,
        "source": "gaussian-preflight",
        "range": {
            "start": {"line": line0, "character": col0},
            "end": {"line": line0, "character": col0 + 1},
        },
        "blocking": blocking,
        "fix_hints": fix_hints,
        "source_provenance": source_provenance,
    }
    if actions:
        payload["actions"] = actions
    if facts:
        payload["facts"] = facts
    if artifact_roles:
        payload["artifact_roles"] = artifact_roles
    if domain_tags:
        payload["domain_tags"] = domain_tags
    if version_assumption:
        payload["version_assumption"] = version_assumption
    if manual_ref:
        payload["manual_ref"] = manual_ref
    if intent:
        payload["intent"] = intent
    return payload


def _missing_route_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    node = next(iter(graph.by_role(ROLE_CONTROL)), None)
    if node is not None and not node.exists:
        # The route card is the mandatory control deck; without it Gaussian
        # cannot decide what to compute. This is the most severe preflight gap.
        out.append(
            _diag(
                code=CODE_MISSING_ROUTE,
                severity="error",
                message=(
                    "Route card ('# ... ') is missing; Gaussian requires it as the "
                    "control deck for every job"
                ),
                path=path,
                line=1,
                category="cross-file reference",
                confidence=0.97,
                blocking=True,
                source_provenance={
                    "role": ROLE_CONTROL,
                    "expected_section": "route",
                    "route_present": False,
                },
                fix_hints=[
                    "Add a '# ... ' route card with method, basis, and job type",
                    "Or restore the route from the original template",
                ],
                actions=[
                    {
                        "kind": "insert_route",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"route_present": False},
                artifact_roles=[ROLE_CONTROL, ROLE_PRIMARY_INPUT],
                domain_tags=["cross-section", "blocking"],
            )
        )
    return out


def _structure_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    node = next(iter(graph.by_role(ROLE_STRUCTURE)), None)
    if node is None:
        return out
    # The molecule spec must contain atom geometry after the charge/mult line.
    if node.exists and len(job.atoms) == 0:
        out.append(
            _diag(
                code=CODE_STRUCTURE_EMPTY,
                severity="error",
                message="Molecule spec has no atom lines; geometry is empty",
                path=path,
                line=node.line,
                category="cross-file reference",
                confidence=0.9,
                blocking=True,
                source_provenance={
                    "role": ROLE_STRUCTURE,
                    "section": "molecule",
                    "atom_count": 0,
                },
                fix_hints=[
                    "Add atom records (Symbol x y z) after the charge/multiplicity line",
                    "Or import the geometry from an external coordinate source",
                ],
                actions=[
                    {
                        "kind": "insert_section",
                        "section": "atoms",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"atom_count": 0},
                artifact_roles=[ROLE_STRUCTURE],
                domain_tags=["cross-section", "blocking"],
            )
        )
    elif not node.exists:
        # Molecule spec entirely absent (no charge/mult line, no atoms).
        out.append(
            _diag(
                code=CODE_STRUCTURE_EMPTY,
                severity="error",
                message=("Molecule specification (charge/multiplicity + atoms) is missing"),
                path=path,
                line=node.line,
                category="cross-file reference",
                confidence=0.93,
                blocking=True,
                source_provenance={
                    "role": ROLE_STRUCTURE,
                    "section": "molecule",
                    "atom_count": 0,
                },
                fix_hints=[
                    "Add a charge/multiplicity line followed by atom records",
                    "Example: '0 1\\nO 0.0 0.0 0.0\\nH 0.0 0.0 1.0\\nH 0.0 1.0 0.0'",
                ],
                actions=[
                    {
                        "kind": "insert_section",
                        "section": "molecule",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"atom_count": 0},
                artifact_roles=[ROLE_STRUCTURE],
                domain_tags=["cross-section", "blocking"],
            )
        )
    return out


def _basis_diagnostics(graph: ArtifactGraph, job: GaussianJob, path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    basis_node = next(iter(graph.by_role(ROLE_BASIS)), None)
    control_node = next(iter(graph.by_role(ROLE_CONTROL)), None)
    if basis_node is None or control_node is None or not control_node.exists:
        return out
    if basis_node.exists:
        return out
    # No basis keyword, no gen/genecp, no @file, no inline gen basis. Gaussian
    # cannot proceed without a basis declaration.
    out.append(
        _diag(
            code=CODE_MISSING_BASIS,
            severity="error",
            message=(
                "No basis set declared in the route (no basis keyword, 'gen', "
                "'genecp', or '@file.gbs' external basis)"
            ),
            path=path,
            line=control_node.line,
            category="cross-file reference",
            confidence=0.95,
            blocking=True,
            source_provenance={
                "role": ROLE_BASIS,
                "control_route": job.route_section,
                "basis_keyword": False,
                "gen": False,
                "external_file": False,
            },
            fix_hints=[
                "Add a basis-set keyword to the route (e.g. '# B3LYP/6-31G*')",
                "Or use 'gen' with an external '@basis.gbs' file",
                "Or use 'genecp' when pairing an all-electron basis with an ECP",
            ],
            actions=[
                {
                    "kind": "set_route_basis",
                    "value": "6-31G*",
                    "target": str(path),
                    "safe_to_auto_apply": False,
                }
            ],
            facts={
                "basis_keyword": False,
                "gen": False,
                "external_file": False,
            },
            artifact_roles=[ROLE_BASIS, ROLE_CONTROL],
            domain_tags=["cross-section", "blocking"],
        )
    )
    return out


def _guess_oldchk_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    guess_node = next(iter(graph.by_role(ROLE_GUESS)), None)
    if guess_node is None or guess_node.detail is None:
        return out
    guess_read = bool(guess_node.detail.get("guess_read"))
    has_oldchk = bool(guess_node.detail.get("oldchk"))
    if not guess_read:
        return out
    # guess=read restarts SCF from a checkpoint; without %oldchk pointing at the
    # source the restart will fail at SCF startup.
    if not has_oldchk:
        line = guess_node.line
        out.append(
            _diag(
                code=CODE_GUESS_READ_WITHOUT_OLDCHK,
                severity="error",
                message=(
                    "Route declares guess=read but no %oldchk checkpoint was "
                    "supplied to source the restart orbitals"
                ),
                path=path,
                line=line,
                category="cross-file reference",
                confidence=0.92,
                blocking=True,
                source_provenance={
                    "role": ROLE_GUESS,
                    "control_keyword": "guess=read",
                    "oldchk_present": False,
                },
                fix_hints=[
                    "Add '%oldchk=previous.chk' pointing at the source checkpoint",
                    "Or change the route to a self-consistent guess (remove guess=read)",
                ],
                actions=[
                    {
                        "kind": "insert_link0",
                        "command": "oldchk",
                        "value": "previous.chk",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"guess_read": True, "oldchk_present": False},
                artifact_roles=[ROLE_GUESS, ROLE_LINK0],
                domain_tags=["cross-section", "blocking"],
            )
        )
    return out


def _pseudo_basis_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pseudo_node = next(iter(graph.by_role(ROLE_PSEUDOPOTENTIAL)), None)
    basis_node = next(iter(graph.by_role(ROLE_BASIS)), None)
    if pseudo_node is None or basis_node is None:
        return out
    if not pseudo_node.exists:
        return out
    if not basis_node.exists:
        return out  # missing-basis diagnostic already covers the absence.
    detail = basis_node.detail or {}
    declared_functional = _detect_dft_functional(job.route_section)
    route_upper = job.route_section.upper()
    # An ECP/pseudo=read must be paired with an ECP-capable basis family
    # (LANL2DZ, def2-ECP, cc-pVnZ-PP, ...); keeping a tiny all-electron basis
    # while declaring an ECP is a common silent mistake.
    ecp_basis_families = (
        "LANL2DZ",
        "LANL2MB",
        "SDD",
        "DEF2-ECP",
        "DEF2-SD",
        "CC-PVDZ-PP",
        "CC-PVTZ-PP",
        "CC-PVQZ-PP",
        "UGBS",
        "STUTTGART",
    )
    uses_ecp_basis = any(fam in route_upper for fam in ecp_basis_families)
    if not uses_ecp_basis:
        out.append(
            _diag(
                code=CODE_PSEUDO_WITHOUT_BASIS,
                severity="warning",
                message=(
                    "Route declares an ECP (pseudo=read/genecp) but the basis is "
                    "not an ECP-capable family; pair the ECP with LANL2DZ/def2-ECP/"
                    "cc-pVnZ-PP"
                ),
                path=path,
                line=basis_node.line,
                category="semantic consistency",
                confidence=0.8,
                blocking=False,
                source_provenance={
                    "role": ROLE_PSEUDOPOTENTIAL,
                    "cross_referenced_role": ROLE_BASIS,
                    "basis_detail": detail,
                    "functional": declared_functional,
                },
                fix_hints=[
                    "Switch the basis to an ECP family (LANL2DZ, def2-ECP, ...)",
                    "Or remove the ECP if an all-electron basis is intentional",
                ],
                actions=[
                    {
                        "kind": "set_route_basis",
                        "value": "LANL2DZ",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"ecp_basis_family": False, "pseudo_declared": True},
                artifact_roles=[ROLE_PSEUDOPOTENTIAL, ROLE_BASIS],
                domain_tags=["semantic", "non-blocking"],
            )
        )
    return out


def _low_mem_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path, intent: dict[str, Any] | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    link0_node = next(iter(graph.by_role(ROLE_LINK0)), None)
    if link0_node is None:
        return out
    mem_value = job.link0.get("mem")
    if not mem_value:
        return out
    mb = _parse_mem_mb(mem_value)
    if mb is None:
        return out
    threshold = float((intent or {}).get("mem_warning_mb", DEFAULT_MEM_WARNING_MB))
    if mb < threshold:
        out.append(
            _diag(
                code=CODE_LOW_MEM,
                severity="warning",
                message=(
                    f"%mem={mem_value} (~{mb:g} MB) is below the conservative workflow "
                    f"threshold ({threshold:g} MB); large jobs may spill to disk"
                ),
                path=path,
                line=link0_node.line,
                category="preflight/runtime-risk",
                confidence=0.75,
                blocking=False,
                source_provenance={
                    "role": ROLE_LINK0,
                    "command": "mem",
                    "threshold_source": (
                        "intent" if "mem_warning_mb" in (intent or {}) else "default"
                    ),
                },
                fix_hints=[
                    f"Raise %mem to at least {threshold:g} MB",
                    "Or document the smaller allocation in the intent contract",
                ],
                actions=[
                    {
                        "kind": "set_link0",
                        "command": "mem",
                        "value": f"{int(threshold)}MB",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"mem_mb": mb, "threshold_mb": threshold, "raw": mem_value},
                artifact_roles=[ROLE_LINK0, ROLE_PRIMARY_INPUT],
                domain_tags=["preflight", "runtime-risk"],
            )
        )
    return out


def _opt_maxcycle_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    opt_node = next(iter(graph.by_role(ROLE_OPTIMIZATION)), None)
    if opt_node is None or not opt_node.exists:
        return out
    maxcycle = _extract_route_int(job.route_section, "MAXCYCLE")
    if maxcycle is None:
        return out
    if maxcycle <= DEFAULT_OPT_MAXCYCLE_WARNING_FLOOR:
        out.append(
            _diag(
                code=CODE_OPT_MAXCYCLE_DISABLED,
                severity="warning",
                message=(
                    f"OPT job but MaxCycle={maxcycle} allows at most {maxcycle} "
                    "optimization step(s); geometry will likely not converge"
                ),
                path=path,
                line=opt_node.line,
                category="semantic consistency",
                confidence=0.85,
                blocking=False,
                source_provenance={
                    "role": ROLE_OPTIMIZATION,
                    "control_job": "OPT",
                    "maxcycle": maxcycle,
                },
                fix_hints=[
                    "Raise MaxCycle to a realistic number of allowed steps (e.g. 100)",
                    "Or remove the explicit MaxCycle to use the Gaussian default",
                ],
                actions=[
                    {
                        "kind": "set_route_keyword",
                        "keyword": "MaxCycle",
                        "value": "100",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"opt": True, "maxcycle": maxcycle},
                artifact_roles=[ROLE_OPTIMIZATION, ROLE_CONTROL],
                domain_tags=["semantic", "non-blocking"],
            )
        )
    return out


def _method_basis_mismatch_diagnostics(
    graph: ArtifactGraph, job: GaussianJob, path: Path, version_assumption: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    control_node = next(iter(graph.by_role(ROLE_CONTROL)), None)
    if control_node is None or not control_node.exists:
        return out
    route_tokens = {tok.upper() for tok in _route_tokens(job.route_section)}
    correlated = sorted(_CORRELATED_METHOD_TOKENS & route_tokens)
    if not correlated:
        return out
    minimal = sorted(_MINIMAL_BASIS_TOKENS & route_tokens)
    if not minimal:
        return out
    method = correlated[0]
    basis = minimal[0]
    # Correlated methods (MP2/CCSD/...) on a minimal basis produce noise; surface
    # this as a version/method compatibility finding the parent probe can act on.
    out.append(
        _diag(
            code=CODE_METHOD_BASIS_MISMATCH,
            severity="error",
            message=(
                f"Correlated method {method} is not meaningful with the minimal " f"basis {basis}"
            ),
            path=path,
            line=control_node.line,
            category="schema",
            confidence=0.9,
            blocking=True,
            source_provenance={
                "role": ROLE_BASIS,
                "method": method,
                "basis": basis,
                "schema_source": "gaussian-lsp builtin method/basis matrix",
            },
            fix_hints=[
                f"Switch the basis to a polarized family for {method} (e.g. 6-31G*)",
                "Or downgrade to a single-point HF calculation",
            ],
            actions=[
                {
                    "kind": "set_route_basis",
                    "value": "6-31G*",
                    "target": str(path),
                    "safe_to_auto_apply": False,
                }
            ],
            facts={"method": method, "basis": basis},
            artifact_roles=[ROLE_BASIS, ROLE_CONTROL],
            domain_tags=["schema", "version-aware", "blocking"],
            version_assumption=version_assumption,
        )
    )
    return out


def _dft_without_functional_diagnostics(
    graph: ArtifactGraph,
    job: GaussianJob,
    path: Path,
    version_assumption: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    control_node = next(iter(graph.by_role(ROLE_CONTROL)), None)
    if control_node is None or not control_node.exists:
        return out
    route_upper = job.route_section.upper()
    # The route uses a DFT token but the functional cannot be resolved to a
    # known functional name. This is the DFTTYP-without-functional analog.
    has_dft_route_marker = " DFT" in route_upper or "TD=" in route_upper
    functional = _detect_dft_functional(job.route_section)
    if has_dft_route_marker and functional is None:
        out.append(
            _diag(
                code=CODE_DFT_WITHOUT_FUNCTIONAL,
                severity="error",
                message=(
                    "Route references DFT but no recognizable functional "
                    "(B3LYP/PBE/...) was supplied"
                ),
                path=path,
                line=control_node.line,
                category="schema",
                confidence=0.9,
                blocking=True,
                source_provenance={
                    "role": ROLE_DFT,
                    "keyword": "dft marker",
                    "schema_source": "gaussian-lsp builtin functional schema",
                },
                fix_hints=[
                    "Set a functional such as B3LYP, PBE0, or wB97X-D in the route",
                    "Or remove the DFT marker for a pure Hartree-Fock run",
                ],
                actions=[
                    {
                        "kind": "set_route_method",
                        "value": "B3LYP",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"functional": None},
                artifact_roles=[ROLE_DFT, ROLE_CONTROL],
                domain_tags=["schema", "version-aware", "blocking"],
                version_assumption=version_assumption,
            )
        )
    return out


# --- version-aware-keywords ------------------------------------------------


def resolve_version_assumption(intent: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve the explicit runtime/version assumption for this preflight run.

    When the exact runtime/image version is unknown we record that fact
    explicitly rather than guessing, per the issue's version-assumptions
    acceptance criterion. The intent contract can override ``software_version``
    (e.g. ``gaussian >=g16``); otherwise we fall back to the schema version the
    builtin keyword set was authored against.
    """
    intent = intent or {}
    software_version = intent.get("software_version")
    runtime_image = intent.get("runtime_image")
    assumption: dict[str, Any] = {
        "software": "gaussian",
        "software_version": software_version or "unknown",
        "runtime_image": runtime_image or "unknown",
        "schema_source": intent.get("schema_source", "gaussian-lsp builtin"),
        # The fallback is intentional and explicit so consumers never have to
        # guess whether ``unknown`` means "not checked" or "could not determine".
        "exact_runtime_known": bool(software_version or runtime_image),
    }
    if software_version or runtime_image:
        assumption["declared_by"] = "intent"
    else:
        assumption["declared_by"] = "fallback"
    return assumption


def _version_assumption_diagnostic(
    version_assumption: dict[str, Any],
    intent: dict[str, Any] | None,
    path: Path,
) -> list[dict[str, Any]]:
    """Emit an explicit information diagnostic when the runtime version is unknown.

    This makes the version assumption machine-readable in the diagnostic stream
    itself (not just metadata) so the parent probe can surface it without
    parsing the envelope top-level.
    """
    if version_assumption["exact_runtime_known"]:
        return []
    return [
        _diag(
            code=CODE_VERSION_ASSUMPTION,
            severity="information",
            message=(
                "Exact Gaussian runtime/image version is unknown; preflight "
                "validated against the builtin keyword set"
            ),
            path=path,
            line=1,
            category="preflight/runtime-risk",
            confidence=1.0,
            blocking=False,
            source_provenance={
                "role": ROLE_PRIMARY_INPUT,
                "reason": "software_version and runtime_image not declared in intent",
            },
            fix_hints=[
                "Declare software_version/runtime_image in the intent contract",
            ],
            actions=[],
            facts={
                "software_version": version_assumption["software_version"],
                "runtime_image": version_assumption["runtime_image"],
                "schema_source": version_assumption["schema_source"],
            },
            artifact_roles=[ROLE_PRIMARY_INPUT],
            domain_tags=["version-aware", "assumption"],
            version_assumption=version_assumption,
            intent=dict(intent) if intent else None,
        )
    ]


# --- fleet-regression-fixtures --------------------------------------------


def fleet_manifest(
    *,
    fixtures: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a machine-readable preflight manifest for the parent fleet.

    The parent ``bohrium_skills`` probe/report workflow consumes this to know
    which preflight codes exist, which capabilities are implemented, and which
    fixtures exercise them. Keeping it as data (not README prose) means the
    fleet regression evidence stays in sync with the implementation.
    """
    codes = {
        CODE_MISSING_ROUTE: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "mandatory route card ('# ... ') absent from input",
        },
        CODE_STRUCTURE_EMPTY: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "molecule spec missing or has no atom geometry lines",
        },
        CODE_MISSING_BASIS: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "no basis keyword / gen / @file / inline basis declared",
        },
        CODE_GUESS_READ_WITHOUT_OLDCHK: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "guess=read without a matching %oldchk checkpoint",
        },
        CODE_PSEUDO_WITHOUT_BASIS: {
            "severity": "warning",
            "category": "semantic consistency",
            "blocking": False,
            "capability": "cross-artifact-graph",
            "summary": "ECP declared without an ECP-capable basis family",
        },
        CODE_LOW_MEM: {
            "severity": "warning",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "%mem allocation below conservative threshold",
        },
        CODE_OPT_MAXCYCLE_DISABLED: {
            "severity": "warning",
            "category": "semantic consistency",
            "blocking": False,
            "capability": "cross-artifact-graph",
            "summary": "OPT job with MaxCycle<=1",
        },
        CODE_METHOD_BASIS_MISMATCH: {
            "severity": "error",
            "category": "schema",
            "blocking": True,
            "capability": "version-aware-keywords",
            "summary": "correlated method on a minimal basis",
        },
        CODE_DFT_WITHOUT_FUNCTIONAL: {
            "severity": "error",
            "category": "schema",
            "blocking": True,
            "capability": "version-aware-keywords",
            "summary": "DFT route without a recognizable functional",
        },
        CODE_VERSION_ASSUMPTION: {
            "severity": "information",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "exact runtime version unknown; fallback schema used",
        },
    }
    capabilities = {
        "version-aware-keywords": {
            "status": "available",
            "evidence_codes": [
                CODE_METHOD_BASIS_MISMATCH,
                CODE_DFT_WITHOUT_FUNCTIONAL,
                CODE_VERSION_ASSUMPTION,
                CODE_LOW_MEM,
            ],
        },
        "cross-artifact-graph": {
            "status": "available",
            "roles": list(ALL_ROLES),
            "evidence_codes": [
                CODE_MISSING_ROUTE,
                CODE_STRUCTURE_EMPTY,
                CODE_MISSING_BASIS,
                CODE_GUESS_READ_WITHOUT_OLDCHK,
                CODE_PSEUDO_WITHOUT_BASIS,
                CODE_OPT_MAXCYCLE_DISABLED,
            ],
        },
        "code-actions": {
            "status": "available",
            "blocking_gate": "gaussian-lsp-tool check --fail-on-blocking",
            "evidence_codes": list(codes.keys()),
        },
        "fleet-regression-fixtures": {
            "status": "available",
            "fixtures": list(fixtures) if fixtures else [],
        },
    }
    return {
        "software": "gaussian",
        "preflight_envelope": "DiagnosticEnvelope/v1",
        "artifact_roles": list(ALL_ROLES),
        "capabilities": capabilities,
        "codes": codes,
    }


# --- helpers ---------------------------------------------------------------


def _route_tokens(route_section: str) -> list[str]:
    """Tokenize a route section into uppercase keyword tokens.

    Gaussian route syntax is free-form (``# B3LYP/6-31G* opt``); tokens are
    separated by whitespace, ``/``, ``,``, and ``=``. We strip the leading
    ``#``/``--``/``#n``/``#p`` verbosity marker so it does not pollute the
    keyword set.
    """
    if not route_section:
        return []
    # Strip the opening route marker (``#``, ``--``, ``#n``, ``#p``, ``#t``).
    body = re.sub(r"^\s*[#\-]+[nptNPT]?\s*", "", route_section)
    tokens = re.split(r"[\s/,=]+", body)
    return [tok for tok in tokens if tok]


def _detect_dft_functional(route_section: str) -> str | None:
    """Return the DFT functional token if the route names a known one.

    We match against the builtin GAUSSIAN_METHODS list (which already includes
    DFT functionals like B3LYP, PBE0, wB97X-D, ...). Returns the original-case
    token so consumers can echo it back verbatim.
    """
    if not route_section:
        return None
    known = {m.upper(): m for m in GAUSSIAN_METHODS}
    for tok in _route_tokens(route_section):
        upper = tok.upper()
        if upper in known:
            return known[upper]
    return None


def _extract_route_int(route_section: str, keyword: str) -> int | None:
    """Extract an integer route keyword value (e.g. ``opt=(MaxCycle=2)``)."""
    if not route_section:
        return None
    # Match ``Keyword=N`` and ``Keyword=(... N ...)`` for the given keyword.
    pattern = re.compile(rf"\b{re.escape(keyword)}\s*=\s*\(?(\d+)", re.IGNORECASE)
    match = pattern.search(route_section)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except (ValueError, IndexError):
        return None


def _parse_mem_mb(raw: str) -> float | None:
    """Parse a Gaussian %mem value into megabytes.

    Gaussian accepts values like ``4GB``, ``512MW`` (megawords), ``2000MB``,
    or a bare byte count. Returns ``None`` when the value cannot be parsed.
    """
    if not raw:
        return None
    text = raw.strip().upper()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(KW|MW|GB|MB|KB|GW|B)?$", text)
    if match is None:
        return None
    try:
        amount = float(match.group(1))
    except ValueError:
        return None
    unit = match.group(2) or ""
    if unit in {"", "B"}:
        return amount / (1024.0 * 1024.0)
    if unit == "KB":
        return amount / 1024.0
    if unit == "MB":
        return amount
    if unit == "GB":
        return amount * 1024.0
    if unit == "KW":
        # Kilowords; assume 8-byte doubles (Gaussian default).
        return amount * 1024.0 * 8.0 / (1024.0 * 1024.0)
    if unit == "MW":
        return amount * 1024.0 * 8.0
    if unit == "GW":
        return amount * 1024.0 * 1024.0
    return None


# Used by the tool layer to detect a Gaussian input without parsing the whole
# file, so a single-line probe stays cheap.
_ROUTE_MARKER_RE = re.compile(r"^\s*[#\-]{1,2}[nptNPT]?\s", re.MULTILINE)
_LINK0_RE = re.compile(r"^\s*%[A-Za-z]", re.MULTILINE)


def looks_like_gaussian_workspace(path: Path) -> bool:
    """True when a path is a real Gaussian generated-input artifact.

    Preflight accepts either a ``.gjf``/``.com`` file or a directory containing
    one; a directory with no Gaussian input falls back to the legacy
    single-file lint path so callers that progressively build inputs are not
    flooded with blocking missing-route errors before the input exists.

    For a single file we require *both* a route marker and a molecule
    specification (a charge/multiplicity line) so a bare progressive fragment
    like ``# bad`` does not trigger the cross-artifact preflight checks; the
    legacy single-file lint path still runs on such fragments.
    """
    if path.is_file():
        return _looks_like_complete_gaussian_file(path)
    if not path.is_dir():
        return False
    return any(_has_gaussian_entry(child) for child in path.iterdir())


def _has_gaussian_entry(child: Path) -> bool:
    if child.is_file():
        suffix = child.suffix.lower()
        if suffix in {".gjf", ".com"} or _has_gaussian_marker(child):
            return True
    return False


def _has_gaussian_marker(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return bool(_ROUTE_MARKER_RE.search(text)) or bool(_LINK0_RE.search(text))


# Charge/multiplicity line: ``<int> <int>`` (e.g. ``0 1``). Used to distinguish a
# complete generated input (route + title + molecule spec) from a progressive
# fragment (just a route card), so the cross-artifact preflight does not fire on
# a half-typed file the legacy single-file lint already handles.
_CHARGE_MULT_RE = re.compile(r"^\s*[+-]?\d+\s+\d+\s*$", re.MULTILINE)


def _looks_like_complete_gaussian_file(path: Path) -> bool:
    """True when a single file carries both a route marker and a molecule spec.

    A bare route fragment (``# bad``) is intentionally *not* a workspace: it
    has no charge/multiplicity line and no atoms, so the cross-artifact checks
    would only add noise on top of the legacy single-file lint. Once the user
    adds the molecule spec, preflight kicks in.
    """
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    has_route = bool(_ROUTE_MARKER_RE.search(text)) or bool(_LINK0_RE.search(text))
    if not has_route and suffix not in {".gjf", ".com"}:
        return False
    if suffix in {".gjf", ".com"} and not has_route:
        # A .gjf/.com file with no route at all is not a real Gaussian input.
        return False
    return bool(_CHARGE_MULT_RE.search(text))
