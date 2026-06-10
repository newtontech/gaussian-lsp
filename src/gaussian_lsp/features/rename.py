"""LSP rename provider for Gaussian input files.

This module provides rename refactoring support for Gaussian .gjf/.com files.
It supports renaming Z-matrix variables (definitions and references within
geometry lines), while safely rejecting keywords, route tokens, section
names, and ambiguous or unsupported targets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from lsprotocol.types import Position, Range, TextEdit, WorkspaceEdit
from pygls.server import LanguageServer

from ..parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
    LINK0_COMMANDS,
    GJFParser,
)


@dataclass(frozen=True)
class VariableOccurrence:
    """A single occurrence of a Z-matrix variable reference or definition."""

    line: int
    start_col: int
    end_col: int
    kind: str  # "definition" | "reference"


@dataclass(frozen=True)
class RenameTarget:
    """Describes what is being renamed and its scope."""

    name: str
    kind: str  # "variable"
    occurrences: Tuple[VariableOccurrence, ...]


# Z-matrix variable definition: NAME=numeric_value
_VAR_DEF_PATTERN = re.compile(
    r"^\s*([A-Za-z]\w*)\s*=\s*" + r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[Ee][+-]?\d+)?\s*$"
)

# A Z-matrix reference in a geometry line is a non-numeric token at an
# even position (2, 4, 6) within a Z-matrix coordinate spec.  We identify
# candidates by matching word tokens that are NOT pure integers and NOT
# valid element symbols.
_WORD_TOKEN = re.compile(r"[A-Za-z_]\w*")


def _canonical_element(element: str) -> str:
    """Normalize a Gaussian element token to an element symbol."""
    clean = element.split("(")[0]
    return clean[:1].upper() + clean[1:].lower() if clean else clean


def _is_gaussian_keyword(word: str) -> bool:
    """Return True if *word* is a recognized Gaussian keyword."""
    word_upper = word.upper()
    if word_upper in {m.upper() for m in GAUSSIAN_METHODS}:
        return True
    if word_upper in {b.upper() for b in GAUSSIAN_BASIS_SETS}:
        return True
    if word_upper in {j.upper() for j in GAUSSIAN_JOB_TYPES}:
        return True
    if word_upper in {cmd.upper() for cmd in LINK0_COMMANDS}:
        return True
    # Common route keywords
    _ROUTE_KEYWORDS = {
        "OPT",
        "FREQ",
        "SP",
        "NMR",
        "POP",
        "DENSITY",
        "SCF",
        "GUESS",
        "POP",
        "NOSYMM",
        "SYMM",
        "INT",
        "GRID",
        "TIGHT",
        "LOOSE",
        "MAXCYCLE",
        "MAXDISK",
        "CHK",
        "RWF",
        "SCRATCH",
        "MEM",
        "NPROC",
        "NPROCSHARED",
    }
    if word_upper in _ROUTE_KEYWORDS:
        return True
    return False


def _is_valid_variable_name(name: str) -> bool:
    """Return True if *name* is an acceptable Gaussian Z-matrix variable name."""
    if not name:
        return False
    return bool(re.match(r"^[A-Za-z_]\w*$", name))


def _find_sections(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Find the charge/multiplicity line and the blank line ending the geometry block.

    Returns (charge_line_index, geometry_end_line_index) or (None, None).
    """
    lines = text.splitlines()
    parser = GJFParser()
    charge_line: Optional[int] = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if parser.CHARGE_MULT_PATTERN.match(stripped):
            charge_line = i
            break

    if charge_line is None:
        return None, None

    # Walk geometry lines after charge/mult until blank line
    geometry_end: Optional[int] = None
    geometry_started = False
    for i in range(charge_line + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            if geometry_started:
                geometry_end = i
                break
            continue
        geometry_started = True

    return charge_line, geometry_end


def _collect_variable_occurrences(text: str, var_name: str) -> List[VariableOccurrence]:
    """Find every definition and reference of a Z-matrix variable in *text*.

    Args:
        text: Full document text.
        var_name: The variable name to search for (case-sensitive).

    Returns:
        Sorted list of VariableOccurrence objects.
    """
    occurrences: List[VariableOccurrence] = []
    lines = text.splitlines()
    charge_line, geometry_end = _find_sections(text)

    # Collect definitions (lines after geometry that match NAME=value)
    # and references within geometry lines.
    search_start = (geometry_end + 1) if geometry_end is not None else len(lines)

    # --- Find definitions after geometry block ---
    for i in range(search_start, len(lines)):
        line = lines[i]
        m = _VAR_DEF_PATTERN.match(line)
        if m and m.group(1) == var_name:
            occurrences.append(
                VariableOccurrence(
                    line=i,
                    start_col=m.start(1),
                    end_col=m.end(1),
                    kind="definition",
                )
            )

    # --- Find references within geometry lines ---
    if charge_line is not None:
        geom_start = charge_line + 1
        geom_end = geometry_end if geometry_end is not None else len(lines)

        for i in range(geom_start, geom_end):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if not parts:
                continue

            # Check if this is a Z-matrix line (not a Cartesian line)
            # Z-matrix lines have 1, 3, 5, or 7 parts and non-Cartesian values
            if len(parts) < 3:
                # First atom in Z-matrix has only the element symbol
                continue

            # In Z-matrix format, positions 2, 4, 6 (0-indexed) contain
            # values that may be variable references
            for pos in range(2, len(parts), 2):
                token = parts[pos]
                if token == var_name:
                    # Calculate the column position of this token in the original line
                    col_start = _find_token_col(line, token, pos, parts)
                    col_end = col_start + len(token)
                    occurrences.append(
                        VariableOccurrence(
                            line=i,
                            start_col=col_start,
                            end_col=col_end,
                            kind="reference",
                        )
                    )

    return sorted(occurrences, key=lambda o: (o.line, o.start_col))


def _find_token_col(line: str, token: str, token_index: int, parts: List[str]) -> int:
    """Find the column position of a specific token occurrence in a line.

    We search for the nth occurrence (by token_index) of the token value
    to handle cases where the same value appears multiple times.
    """
    col = 0
    search_count = 0
    token_lower = token.lower()

    # Walk through the line character by character to find word tokens
    i = 0
    while i < len(line):
        if line[i].isalnum() or line[i] == "_":
            start = i
            while i < len(line) and (line[i].isalnum() or line[i] == "_"):
                i += 1
            if line[start:i].lower() == token_lower:
                if search_count == token_index:
                    return start
                search_count += 1
        else:
            i += 1

    # Fallback: reconstruct position from parts
    col = 0
    for j in range(token_index):
        # Find the position of parts[j] starting from col
        idx = line.find(parts[j], col)
        if idx >= 0:
            col = idx + len(parts[j])
    idx = line.find(token, col)
    return idx if idx >= 0 else col


class RenameProvider:
    """Provides rename support for Gaussian input files."""

    def __init__(self, server: Optional[LanguageServer] = None) -> None:
        """Initialize the rename provider.

        Args:
            server: The language server instance.
        """
        self.server = server

    # ------------------------------------------------------------------
    # prepareRename
    # ------------------------------------------------------------------

    def prepare_rename(
        self,
        text: str,
        position: Position,
    ) -> Optional[Range]:
        """Validate that the symbol at *position* can be renamed.

        Returns the Range of the symbol if renameable, or None.

        Renameable targets:
          - Z-matrix variable definitions (NAME=value lines after geometry)
          - Z-matrix variable references within geometry lines

        Rejected targets:
          - Gaussian keywords, methods, basis sets, job types
          - Route section tokens
          - Element symbols
          - Arbitrary words that are not recognised symbols
          - Empty positions or out-of-range lines
        """
        lines = text.splitlines()
        if position.line >= len(lines) or position.line < 0:
            return None

        line = lines[position.line]
        charge_line, geometry_end = _find_sections(text)

        # Check if we are on a variable definition line (after geometry)
        if geometry_end is not None and position.line >= geometry_end:
            m = _VAR_DEF_PATTERN.match(line)
            if m and m.start(1) <= position.character <= m.end(1):
                return Range(
                    start=Position(line=position.line, character=m.start(1)),
                    end=Position(line=position.line, character=m.end(1)),
                )

        # Check if we are on a Z-matrix variable reference in geometry
        if charge_line is not None and charge_line < position.line:
            if geometry_end is not None and position.line >= geometry_end:
                return None  # Already checked above

            stripped = line.strip()
            parts = stripped.split()
            if len(parts) >= 3:
                # Check if this is a Z-matrix line (has non-numeric, non-element tokens)
                for pos in range(2, len(parts), 2):
                    token = parts[pos]
                    if (
                        not token.replace(".", "")
                        .replace("-", "")
                        .replace("+", "")
                        .replace("e", "")
                        .replace("E", "")
                        .isdigit()
                    ):
                        # It's a potential variable reference
                        if not _looks_like_number(token):
                            col_start = _find_token_col(line, token, pos, parts)
                            col_end = col_start + len(token)
                            if col_start <= position.character <= col_end:
                                # Verify it's actually a defined variable
                                var_name = token
                                occs = _collect_variable_occurrences(text, var_name)
                                has_def = any(o.kind == "definition" for o in occs)
                                if has_def:
                                    return Range(
                                        start=Position(line=position.line, character=col_start),
                                        end=Position(line=position.line, character=col_end),
                                    )

        return None

    # ------------------------------------------------------------------
    # rename
    # ------------------------------------------------------------------

    def get_rename_edits(
        self,
        text: str,
        uri: str,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        """Get workspace edits for renaming a symbol.

        Args:
            text: Document text.
            uri: Document URI.
            position: Cursor position.
            new_name: The new name for the symbol.

        Returns:
            WorkspaceEdit with changes, or None if rename is not valid.
        """
        lines = text.splitlines()
        if position.line >= len(lines) or position.line < 0:
            return None

        target = self._identify_target(text, position)

        if target is None:
            return None

        if target.kind == "variable":
            return self._rename_variable(text, uri, target, new_name)

        return None

    # ------------------------------------------------------------------
    # is_valid_rename
    # ------------------------------------------------------------------

    def is_valid_rename(
        self,
        text: str,
        position: Position,
        new_name: str,
    ) -> bool:
        """Check if a rename operation is valid.

        Args:
            text: Document text.
            position: Cursor position.
            new_name: The new name for the symbol.

        Returns:
            True if rename is valid.
        """
        lines = text.splitlines()
        if position.line >= len(lines) or position.line < 0:
            return False

        target = self._identify_target(text, position)
        if target is None:
            return False

        if target.kind == "variable":
            return _is_valid_variable_name(new_name)

        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _identify_target(
        self,
        text: str,
        position: Position,
    ) -> Optional[RenameTarget]:
        """Identify the renameable symbol under the cursor.

        Returns a RenameTarget, or None if the cursor is not on a
        renameable symbol.
        """
        lines = text.splitlines()
        if position.line >= len(lines):
            return None

        line = lines[position.line]
        charge_line, geometry_end = _find_sections(text)

        # Check variable definition (NAME=value after geometry)
        if geometry_end is not None and position.line >= geometry_end:
            m = _VAR_DEF_PATTERN.match(line)
            if m and m.start(1) <= position.character <= m.end(1):
                var_name = m.group(1)
                occurrences = _collect_variable_occurrences(text, var_name)
                return RenameTarget(
                    name=var_name,
                    kind="variable",
                    occurrences=tuple(occurrences),
                )

        # Check Z-matrix variable reference in geometry
        if charge_line is not None and charge_line < position.line:
            if geometry_end is not None and position.line >= geometry_end:
                return None

            stripped = line.strip()
            parts = stripped.split()
            if len(parts) >= 3:
                for pos in range(2, len(parts), 2):
                    token = parts[pos]
                    if not _looks_like_number(token):
                        col_start = _find_token_col(line, token, pos, parts)
                        col_end = col_start + len(token)
                        if col_start <= position.character <= col_end:
                            var_name = token
                            occurrences = _collect_variable_occurrences(text, var_name)
                            has_def = any(o.kind == "definition" for o in occurrences)
                            if not has_def:
                                return None
                            return RenameTarget(
                                name=var_name,
                                kind="variable",
                                occurrences=tuple(occurrences),
                            )

        return None

    def _rename_variable(
        self,
        text: str,
        uri: str,
        target: RenameTarget,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        """Build workspace edits for a variable rename.

        Args:
            text: Document text (used for validation only).
            uri: Document URI.
            target: The RenameTarget being renamed.
            new_name: New variable name.

        Returns:
            WorkspaceEdit or None if the new name is invalid.
        """
        if not _is_valid_variable_name(new_name):
            return None

        changes: Dict[str, List[TextEdit]] = {uri: []}

        for occ in target.occurrences:
            changes[uri].append(
                TextEdit(
                    range=Range(
                        start=Position(line=occ.line, character=occ.start_col),
                        end=Position(line=occ.line, character=occ.end_col),
                    ),
                    new_text=new_name,
                )
            )

        if not changes[uri]:
            return None

        return WorkspaceEdit(changes=changes)


def _looks_like_number(token: str) -> bool:
    """Return True if the token looks like a numeric literal."""
    return bool(re.match(r"^[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[Ee][+-]?\d+)?$", token))


def get_rename_provider(server: Optional[LanguageServer] = None) -> RenameProvider:
    """Create a rename provider instance.

    Args:
        server: The language server instance.

    Returns:
        Rename provider instance.
    """
    return RenameProvider(server)
