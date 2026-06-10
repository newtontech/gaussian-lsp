"""Code actions provider for Gaussian LSP.

Provides quick fixes for common Gaussian input file errors detected by
the diagnostic and typecheck providers.  Each action produces a minimal
workspace edit that preserves user formatting where practical.

Fix categories
--------------
* Route typo corrections (e.g. ``631G`` -> ``6-31G``).
* Route keyword casing / replacement fixes (e.g. ``optimize`` -> ``opt``).
* Missing route ``#`` prefix.
* Missing blank-line separators between sections.
* Invalid charge/multiplicity value fixes.
* Missing ``%chk`` value.
* Invalid ``%mem`` / ``%nproc`` value fixes.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from lsprotocol.types import (
    CodeAction,
    CodeActionKind,
    Diagnostic,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)

from gaussian_lsp.parser.gjf_parser import GAUSSIAN_BASIS_SETS, GAUSSIAN_METHODS

# Canonical typo -> correction mapping for route tokens.
_ROUTE_TYPO_FIXES: Dict[str, str] = {
    "OPTIMIZE": "opt",
    "OPTIMISE": "opt",
    "FREQENCY": "freq",
    "FREQUENC": "freq",
    "FREQ": "freq",
    "FREQU": "freq",
    "631G": "6-31G",
    "M06-2X": "M062X",
    "NPROCSHARED": "nprocshared",
}

# Edit-distance typo bank for methods and basis sets.
_METHOD_TYPOS: Dict[str, str] = {
    "B3LY": "B3LYP",
    "B3LYO": "B3LYP",
    "BL3YP": "B3LYP",
    "B3LYPP": "B3LYP",
    "B3LYYP": "B3LYP",
    "WB97": "wB97X",
    "WB97XD": "wB97XD",
    "WB97X-D3": "wB97X-D3",
    "M062x": "M062X",
    "M06-2X": "M062X",
    "MO62X": "M062X",
    "PBE0O": "PBE0",
    "PBEO": "PBE0",
    "CAMB3LYP": "CAM-B3LYP",
    "CAM-B3LY": "CAM-B3LYP",
    "CCSDT": "CCSD(T)",
    "CCSD(T)": "CCSD(T)",
}

_BASIS_TYPOS: Dict[str, str] = {
    "6-311": "6-311G",
    "6311G": "6-311G",
    "CC-PVDZ": "cc-pVDZ",
    "CC-PVTZ": "cc-pVTZ",
    "CC-PVQZ": "cc-pVQZ",
    "DEF2TZVP": "def2-TZVP",
    "DEF2-SVPZ": "def2-SVP",
    "LAN2LDZ": "LANL2DZ",
    "LANL2D": "LANL2DZ",
    "STO3G": "STO-3G",
    "STO-3": "STO-3G",
}


class CodeActionProvider:
    """Provides code actions (quick fixes) for Gaussian input files."""

    def __init__(self) -> None:
        """Initialize code actions provider."""
        self._method_set = frozenset(m.upper() for m in GAUSSIAN_METHODS)
        self._basis_set = frozenset(b.upper() for b in GAUSSIAN_BASIS_SETS)

    def get_code_actions(self, source: str, diagnostics: list[Diagnostic]) -> list[CodeAction]:
        """Get code actions for the given source and diagnostics.

        Args:
            source: Full document source text.
            diagnostics: Currently reported diagnostics.

        Returns:
            List of CodeAction objects.
        """
        actions: list[CodeAction] = []

        for diagnostic in diagnostics:
            action = self._get_action_for_diagnostic(source, diagnostic)
            if action is not None:
                actions.append(action)

        actions.extend(self._get_general_actions(source))
        return actions

    # ------------------------------------------------------------------
    # Diagnostic-driven actions
    # ------------------------------------------------------------------

    def _get_action_for_diagnostic(
        self, source: str, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Dispatch a single diagnostic to the appropriate fix handler."""
        message = diagnostic.message.lower()
        line_num = diagnostic.range.start.line
        lines = source.split("\n")

        # --- Route section must start with # ---
        if "route section must start with #" in message or ("missing route section" in message):
            return self._fix_missing_hash(lines, line_num, diagnostic)

        # --- Common route typo hints ---
        # Only apply route typo matching for route-specific diagnostics.
        route_hint_messages = (
            "use freq instead",
            "use opt instead",
            "use m062x instead",
            "did you mean 6-31g",
            "use %nprocshared as a link0 command",
        )
        if any(hint in message for hint in route_hint_messages):
            line_text = lines[line_num].upper() if line_num < len(lines) else ""
            for typo_key, correction in _ROUTE_TYPO_FIXES.items():
                if typo_key.upper() in line_text:
                    return self._fix_route_typo(lines, line_num, diagnostic, typo_key, correction)

        # --- Blank line separators ---
        if "missing blank line after route section" in message:
            return self._insert_blank_line(lines, line_num, diagnostic, before=True)
        if "missing blank line after title section" in message:
            return self._insert_blank_line(lines, line_num, diagnostic, before=True)

        # --- Charge/multiplicity ---
        if "invalid charge/multiplicity" in message:
            return self._fix_charge_mult(lines, line_num, diagnostic)
        if "missing charge/multiplicity" in message:
            return self._insert_charge_mult(lines, line_num, diagnostic)

        # --- Link0 value issues ---
        if "must include a non-empty value" in message:
            return self._fix_empty_link0_value(lines, line_num, diagnostic)
        if "%mem value should include" in message:
            return self._fix_mem_value(lines, line_num, diagnostic)
        if "must be a positive integer" in message:
            return self._fix_nproc_value(lines, line_num, diagnostic)

        # --- Electron parity ---
        if "electron count parity" in message:
            return self._fix_electron_parity(lines, line_num, diagnostic)

        # --- Method typo detection via Levenshtein ---
        if "no recognizable calculation method" in message:
            return self._fix_method_typo(lines, line_num, diagnostic)

        # --- Basis set typo ---
        if "no recognizable basis set" in message:
            return self._fix_basis_typo(lines, line_num, diagnostic)

        # --- SP/OPT mutual exclusion ---
        if "sp and opt are mutually exclusive" in message:
            return self._fix_sp_opt_conflict(lines, line_num, diagnostic)

        return None

    # ------------------------------------------------------------------
    # Individual fix implementations
    # ------------------------------------------------------------------

    def _fix_missing_hash(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> CodeAction:
        """Prepend ``#`` to the route line."""
        line = lines[line_num] if line_num < len(lines) else ""
        return CodeAction(
            title="Add '#' prefix to route section",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=f"# {line}",
                        )
                    ]
                }
            ),
        )

    def _fix_route_typo(
        self,
        lines: list[str],
        line_num: int,
        diagnostic: Diagnostic,
        typo: str,
        correction: str,
    ) -> CodeAction:
        """Replace a known typo token in the route line."""
        line = lines[line_num] if line_num < len(lines) else ""
        # Case-insensitive find-and-replace for the typo token.
        pattern = re.compile(re.escape(typo), re.IGNORECASE)
        new_text = pattern.sub(correction, line)
        return CodeAction(
            title=f"Replace '{typo}' with '{correction}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=new_text,
                        )
                    ]
                }
            ),
        )

    def _insert_blank_line(
        self,
        lines: list[str],
        line_num: int,
        diagnostic: Diagnostic,
        *,
        before: bool = True,
    ) -> CodeAction:
        """Insert a blank line at the diagnostic position."""
        insert_pos = Position(line=line_num if before else line_num + 1, character=0)
        return CodeAction(
            title="Insert missing blank line",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(start=insert_pos, end=insert_pos),
                            new_text="\n",
                        )
                    ]
                }
            ),
        )

    def _fix_charge_mult(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> CodeAction:
        """Suggest ``0 1`` as a safe default charge/multiplicity."""
        line = lines[line_num] if line_num < len(lines) else ""
        return CodeAction(
            title="Replace with '0 1' (neutral singlet)",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text="0 1",
                        )
                    ]
                }
            ),
        )

    def _insert_charge_mult(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> CodeAction:
        """Insert a ``0 1`` charge/multiplicity line before the geometry."""
        insert_pos = Position(line=line_num, character=0)
        return CodeAction(
            title="Insert '0 1' charge/multiplicity line",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(start=insert_pos, end=insert_pos),
                            new_text="0 1\n",
                        )
                    ]
                }
            ),
        )

    def _fix_empty_link0_value(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Suggest adding a placeholder value for empty Link0 keys."""
        line = lines[line_num] if line_num < len(lines) else ""
        stripped = line.strip()
        if "=" not in stripped:
            return None
        key = stripped.split("=", 1)[0].lstrip("%").strip()
        default = "molecule.chk" if key.lower() in ("chk", "oldchk") else "value"
        new_line = f"%{key}={default}"
        return CodeAction(
            title=f"Set %{key} to '{default}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=new_line,
                        )
                    ]
                }
            ),
        )

    def _fix_mem_value(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Suggest a reasonable default ``%mem`` value."""
        line = lines[line_num] if line_num < len(lines) else ""
        stripped = line.strip()
        if "=" not in stripped:
            return None
        key = stripped.split("=", 1)[0].lstrip("%").strip()
        return CodeAction(
            title=f"Set %{key} to '4GB'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=f"%{key}=4GB",
                        )
                    ]
                }
            ),
        )

    def _fix_nproc_value(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Suggest a reasonable default ``%nproc`` value."""
        line = lines[line_num] if line_num < len(lines) else ""
        stripped = line.strip()
        if "=" not in stripped:
            return None
        key = stripped.split("=", 1)[0].lstrip("%").strip()
        return CodeAction(
            title=f"Set %{key} to '4'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=f"%{key}=4",
                        )
                    ]
                }
            ),
        )

    def _fix_electron_parity(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Toggle multiplicity between 1 (singlet) and 2 (doublet)."""
        line = lines[line_num] if line_num < len(lines) else ""
        match = re.match(r"^([+-]?\d+)\s+(\d+)", line.strip())
        if not match:
            return None
        charge = match.group(1)
        mult = int(match.group(2))
        new_mult = 2 if mult == 1 else 1
        new_line = f"{charge} {new_mult}"
        return CodeAction(
            title=f"Change multiplicity to {new_mult}",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=new_line,
                        )
                    ]
                }
            ),
        )

    def _fix_method_typo(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Suggest a close method name via edit distance."""
        line = lines[line_num] if line_num < len(lines) else ""
        route_upper = line.upper().lstrip("#").strip()
        tokens = re.split(r"[\s/=,]+", route_upper)
        for token in tokens:
            if token in self._method_set:
                continue
            suggestion = self._find_closest(token, list(self._method_set))
            if suggestion is not None:
                # Find and replace the original-cased token in the line.
                pattern = re.compile(r"\b" + re.escape(token) + r"\b", re.IGNORECASE)
                new_line = pattern.sub(suggestion, line, count=1)
                return CodeAction(
                    title=f"Replace '{token}' with '{suggestion}'",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diagnostic],
                    edit=WorkspaceEdit(
                        changes={
                            "document": [
                                TextEdit(
                                    range=Range(
                                        start=Position(line=line_num, character=0),
                                        end=Position(line=line_num, character=len(line)),
                                    ),
                                    new_text=new_line,
                                )
                            ]
                        }
                    ),
                )
        return None

    def _fix_basis_typo(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> Optional[CodeAction]:
        """Suggest a close basis set name via edit distance."""
        line = lines[line_num] if line_num < len(lines) else ""
        route_upper = line.upper().lstrip("#").strip()
        tokens = re.split(r"[\s/=,]+", route_upper)
        for token in tokens:
            if token in self._basis_set:
                continue
            suggestion = self._find_closest(token, list(self._basis_set))
            if suggestion is not None:
                pattern = re.compile(r"\b" + re.escape(token) + r"\b", re.IGNORECASE)
                new_line = pattern.sub(suggestion, line, count=1)
                return CodeAction(
                    title=f"Replace '{token}' with '{suggestion}'",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diagnostic],
                    edit=WorkspaceEdit(
                        changes={
                            "document": [
                                TextEdit(
                                    range=Range(
                                        start=Position(line=line_num, character=0),
                                        end=Position(line=line_num, character=len(line)),
                                    ),
                                    new_text=new_line,
                                )
                            ]
                        }
                    ),
                )
        return None

    def _fix_sp_opt_conflict(
        self, lines: list[str], line_num: int, diagnostic: Diagnostic
    ) -> CodeAction:
        """Remove ``SP`` when both ``SP`` and ``OPT`` are present."""
        line = lines[line_num] if line_num < len(lines) else ""
        new_line = re.sub(r"\bSP\b\s*", "", line, count=1, flags=re.IGNORECASE)
        return CodeAction(
            title="Remove 'SP' (OPT takes precedence)",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=0),
                                end=Position(line=line_num, character=len(line)),
                            ),
                            new_text=new_line,
                        )
                    ]
                }
            ),
        )

    # ------------------------------------------------------------------
    # General (non-diagnostic) actions
    # ------------------------------------------------------------------

    def _get_general_actions(self, source: str) -> list[CodeAction]:
        """Return code actions not tied to a specific diagnostic."""
        actions: list[CodeAction] = []
        action = self._create_add_chk_action(source)
        if action is not None:
            actions.append(action)
        return actions

    def _create_add_chk_action(self, source: str) -> Optional[CodeAction]:
        """Create an action to add a missing ``%chk`` directive."""
        lines = source.split("\n")
        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith("%chk="):
                return None
        return CodeAction(
            title="Add '%chk=molecule.chk'",
            kind=CodeActionKind.QuickFix,
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=0, character=0),
                                end=Position(line=0, character=0),
                            ),
                            new_text="%chk=molecule.chk\n",
                        )
                    ]
                }
            ),
        )

    # ------------------------------------------------------------------
    # Similarity helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_closest(token: str, choices: list[str]) -> Optional[str]:
        """Return the closest match from *choices* if similarity > 0.6."""
        token_upper = token.upper()
        if len(token_upper) < 2:
            return None

        # Check known typo banks first.
        for bank in (_METHOD_TYPOS, _BASIS_TYPOS):
            if token_upper in bank:
                return bank[token_upper]

        best_match: Optional[str] = None
        best_score = 0.0
        for choice in choices:
            score = _similarity(token_upper, choice.upper())
            if score > best_score and score > 0.6:
                best_score = score
                best_match = choice
        return best_match


def _similarity(s1: str, s2: str) -> float:
    """Levenshtein-based similarity score in [0, 1]."""
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return 1.0 if len(s1) == 0 else 0.0

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    distance = previous_row[-1]
    max_len = max(len(s1), len(s2))
    return 1.0 - (distance / max_len)


__all__ = ["CodeActionProvider"]
