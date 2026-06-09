"""LSP definition provider for Gaussian input files.

Provides go-to-definition for:

* Route keywords (jump to the route section line where the keyword appears).
* Z-matrix variable references (jump from a variable usage in the geometry
  block to its definition after the geometry).

Missing or unresolved targets return empty results without crashing.
"""

from __future__ import annotations

import re
from typing import List, Optional

from lsprotocol.types import Location, Position, Range

from gaussian_lsp.parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
)

# Re-usable token characters for word extraction.
_TOKEN_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-_()*,.="
)


def _get_word_at_position(line: str, column: int) -> str:
    """Extract the token at *column* in *line*."""
    if not line or column < 0 or column > len(line):
        return ""

    start = column
    end = column

    while start > 0 and line[start - 1] in _TOKEN_CHARS:
        start -= 1

    while end < len(line) and line[end] in _TOKEN_CHARS:
        end += 1

    return line[start:end]


class DefinitionProvider:
    """Provides go-to-definition for Gaussian input files."""

    def __init__(self) -> None:
        """Initialize the definition provider."""
        self._method_set = frozenset(m.upper() for m in GAUSSIAN_METHODS)
        self._basis_set = frozenset(b.upper() for b in GAUSSIAN_BASIS_SETS)
        self._job_type_set = frozenset(jt.upper() for jt in GAUSSIAN_JOB_TYPES)

    def get_definition(
        self,
        source: str,
        uri: str,
        position: Position,
    ) -> Optional[Location]:
        """Return the definition location for the symbol at *position*.

        Args:
            source: Full document text.
            uri: Document URI (used in the returned Location).
            position: Cursor position.

        Returns:
            A Location if a definition is found, otherwise None.
        """
        lines = source.split("\n")
        if position.line >= len(lines):
            return None

        line = lines[position.line]
        word = _get_word_at_position(line, position.character)

        if not word:
            return None

        word_upper = word.upper()

        # 1. Z-matrix variable -> definition line
        loc = self._definition_zmatrix_variable(lines, uri, word, position)
        if loc is not None:
            return loc

        # 2. Route keyword -> route line where keyword appears
        loc = self._definition_route_keyword(lines, uri, word_upper)
        if loc is not None:
            return loc

        return None

    # ------------------------------------------------------------------
    # Z-matrix variable definitions
    # ------------------------------------------------------------------

    def _definition_zmatrix_variable(
        self,
        lines: List[str],
        uri: str,
        word: str,
        position: Position,
    ) -> Optional[Location]:
        """Jump from a Z-matrix variable reference to its definition."""
        charge_line = self._find_charge_line(lines)
        if charge_line is None:
            return None

        if position.line <= charge_line:
            return None

        if not re.match(r"^[A-Za-z]\w*$", word):
            return None

        geometry_end = len(lines)
        for i in range(charge_line + 1, len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                geometry_end = i
                break

        if position.line >= geometry_end:
            return None

        in_geometry = False
        for i in range(charge_line + 1, geometry_end):
            stripped = lines[i].strip()
            parts = stripped.split()
            for part in parts[1:]:
                if part == word:
                    in_geometry = True
                    break
            if in_geometry:
                break

        if not in_geometry:
            return None

        for i in range(geometry_end, len(lines)):
            stripped = lines[i].strip()
            if "=" not in stripped:
                continue
            name, _value = stripped.split("=", 1)
            if name.strip() == word:
                return Location(
                    uri=uri,
                    range=Range(
                        start=Position(line=i, character=0),
                        end=Position(line=i, character=len(stripped)),
                    ),
                )

        return None

    # ------------------------------------------------------------------
    # Route keyword definitions
    # ------------------------------------------------------------------

    def _definition_route_keyword(
        self,
        lines: List[str],
        uri: str,
        word_upper: str,
    ) -> Optional[Location]:
        """Jump to the route line where the keyword appears."""
        if word_upper not in self._method_set and \
           word_upper not in self._basis_set and \
           word_upper not in self._job_type_set:
            return None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue

            route_upper = stripped.upper()
            if word_upper in route_upper:
                col = route_upper.find(word_upper)
                return Location(
                    uri=uri,
                    range=Range(
                        start=Position(line=i, character=col),
                        end=Position(line=i, character=col + len(word_upper)),
                    ),
                )

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_charge_line(lines: List[str]) -> Optional[int]:
        """Return the index of the charge/multiplicity line."""
        pattern = re.compile(r"^[+-]?\d+\s+\d+$")
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                return i
        return None


def get_definition_provider() -> DefinitionProvider:
    """Factory function to create a definition provider.

    Returns:
        A new DefinitionProvider instance.
    """
    return DefinitionProvider()
