"""LSP references provider for Gaussian input files.

Provides find-references for:

* Route keywords (all occurrences in the route section).
* Z-matrix variable references (all usages in geometry + definition).

Unresolved symbols return empty results without crashing.
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
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-_()*,."
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


class ReferencesProvider:
    """Provides find-references for Gaussian input files."""

    def __init__(self) -> None:
        """Initialize the references provider."""
        self._method_set = frozenset(m.upper() for m in GAUSSIAN_METHODS)
        self._basis_set = frozenset(b.upper() for b in GAUSSIAN_BASIS_SETS)
        self._job_type_set = frozenset(jt.upper() for jt in GAUSSIAN_JOB_TYPES)

    def get_references(
        self,
        text: str,
        uri: str,
        position: Position,
        include_declaration: bool = True,
    ) -> List[Location]:
        """Return all references to the symbol at *position*.

        Args:
            text: Full document text.
            uri: Document URI.
            position: Cursor position.
            include_declaration: Whether to include the declaration itself.

        Returns:
            List of Location objects referencing the symbol.
        """
        lines = text.split("\n")
        if position.line >= len(lines):
            return []

        line = lines[position.line]
        word = _get_word_at_position(line, position.character)

        if not word:
            return []

        word_upper = word.upper()
        locations: List[Location] = []

        # 1. Z-matrix variable references
        locations.extend(
            self._references_zmatrix_variable(lines, uri, word, include_declaration)
        )

        # 2. Route keyword references
        locations.extend(
            self._references_route_keyword(lines, uri, word_upper, include_declaration)
        )

        return locations

    # ------------------------------------------------------------------
    # Z-matrix variable references
    # ------------------------------------------------------------------

    def _references_zmatrix_variable(
        self,
        lines: List[str],
        uri: str,
        word: str,
        include_declaration: bool,
    ) -> List[Location]:
        """Find all references to a Z-matrix variable."""
        if not re.match(r"^[A-Za-z]\w*$", word):
            return []

        charge_line = self._find_charge_line(lines)
        if charge_line is None:
            return []

        geometry_end = len(lines)
        for i in range(charge_line + 1, len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                geometry_end = i
                break

        locations: List[Location] = []
        is_zmatrix_variable = False

        for i in range(charge_line + 1, geometry_end):
            stripped = lines[i].strip()
            parts = stripped.split()
            if not parts:
                continue
            for part in parts[1:]:
                if part == word:
                    is_zmatrix_variable = True
                    col = stripped.find(word)
                    locations.append(
                        Location(
                            uri=uri,
                            range=Range(
                                start=Position(line=i, character=col),
                                end=Position(line=i, character=col + len(word)),
                            ),
                        )
                    )
                    break

        for i in range(geometry_end, len(lines)):
            stripped = lines[i].strip()
            if "=" not in stripped:
                continue
            name, _value = stripped.split("=", 1)
            if name.strip() == word:
                is_zmatrix_variable = True
                col = stripped.find(word)
                locations.append(
                    Location(
                        uri=uri,
                        range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(word)),
                        ),
                    )
                )
                break

        if not is_zmatrix_variable:
            return []

        return locations

    # ------------------------------------------------------------------
    # Route keyword references
    # ------------------------------------------------------------------

    def _references_route_keyword(
        self,
        lines: List[str],
        uri: str,
        word_upper: str,
        include_declaration: bool,
    ) -> List[Location]:
        """Find all occurrences of a route keyword in the route section."""
        if word_upper not in self._method_set and \
           word_upper not in self._basis_set and \
           word_upper not in self._job_type_set:
            return []

        locations: List[Location] = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue

            line_upper = stripped.upper()
            start = 0
            while True:
                idx = line_upper.find(word_upper, start)
                if idx == -1:
                    break
                locations.append(
                    Location(
                        uri=uri,
                        range=Range(
                            start=Position(line=i, character=idx),
                            end=Position(line=i, character=idx + len(word_upper)),
                        ),
                    )
                )
                start = idx + 1

        return locations

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


def get_references_provider() -> ReferencesProvider:
    """Factory function to create a references provider.

    Returns:
        A new ReferencesProvider instance.
    """
    return ReferencesProvider()
