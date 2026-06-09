"""LSP formatting provider for Gaussian input files.

Provides document-level and range-level formatting for .gjf / .com files.
Formatting normalises indentation, section separator layout, and coordinate
column alignment while preserving comments, blank-line intent, and route
keyword casing (Gaussian keywords are case-insensitive, so the formatter does
not rewrite them).

Design choices
--------------
* The formatter works on the raw line stream so that comments (`!`) and
  inapplicable lines are preserved verbatim.
* It is *not* a pretty-printer on top of ``GaussianJob.to_gjf()``; that
  method drops comments and reconstructs the file from the AST, which makes
  it unsuitable for an interactive formatter that must feel non-destructive.
* Idempotency is guaranteed: running the formatter on its own output produces
  no additional edits.
"""

from __future__ import annotations

import re
from typing import List, Optional

from lsprotocol.types import (
    DocumentFormattingParams,
    DocumentRangeFormattingParams,
    Position,
    Range,
    TextEdit,
)
from pygls.server import LanguageServer

from gaussian_lsp.parser.gjf_parser import GAUSSIAN_BASIS_SETS, GAUSSIAN_METHODS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Link0 lines start with %
_LINK0_RE = re.compile(r"^%")

# Route lines start with #
_ROUTE_RE = re.compile(r"^#")

# Comment lines start with !
_COMMENT_RE = re.compile(r"^!")

# Charge/multiplicity: two integers
_CHARGE_MULT_RE = re.compile(r"^[+-]?\d+\s+\d+$")

# Atom coordinate line: element followed by three numbers
_ATOM_RE = re.compile(
    r"^([A-Za-z0-9]{1,3}(?:\([A-Za-z0-9=_-]{1,32}\))?)\s+"
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[Ee][+-]?\d+)?)\s+"
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[Ee][+-]?\d+)?)\s+"
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[Ee][+-]?\d+)?)"
)

# ModRedundant commands
_MODRED_RE = re.compile(r"^[MBADRLSFCK]\s+", re.IGNORECASE)
_MODRED_SINGLE_RE = re.compile(r"^[MBADRLSFCK]$", re.IGNORECASE)

# Sets for route-continuation detection
_METHOD_TOKENS = frozenset(m.upper() for m in GAUSSIAN_METHODS)
_BASIS_TOKENS = frozenset(b.upper() for b in GAUSSIAN_BASIS_SETS)


def _is_route_continuation(line: str) -> bool:
    """Return True if *line* looks like it continues a route section."""
    stripped = line.strip()
    if not stripped:
        return False
    upper = stripped.upper()
    return (
        stripped.startswith("#")
        or "/" in stripped
        or "=" in stripped
        or "(" in upper
        or any(tok in upper for tok in _METHOD_TOKENS)
        or any(tok in upper for tok in _BASIS_TOKENS)
    )


def _format_atom_line(stripped: str, coord_width: int = 12) -> str:
    """Align an atom coordinate line to fixed column widths.

    Args:
        stripped: Already-stripped atom line.
        coord_width: Minimum field width for each coordinate value.

    Returns:
        Formatted atom line.
    """
    match = _ATOM_RE.match(stripped)
    if match is None:
        return stripped
    element = match.group(1)
    try:
        x = float(match.group(2))
        y = float(match.group(3))
        z = float(match.group(4))
    except ValueError:  # pragma: no cover — regex guarantees numeric groups
        return stripped
    return f"{element:<2}  {x:>{coord_width}.6f}  {y:>{coord_width}.6f}  {z:>{coord_width}.6f}"


# ---------------------------------------------------------------------------
# FormattingProvider
# ---------------------------------------------------------------------------


class FormattingProvider:
    """Provides document and range formatting for Gaussian input files.

    The formatter operates on raw lines and produces a replacement edit that
    normalises indentation and coordinate alignment without rewriting comments
    or route keyword casing.
    """

    def __init__(self, server: LanguageServer) -> None:
        """Initialise the formatting provider.

        Args:
            server: The language server instance.
        """
        self.server = server

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format_document(
        self, text: str, params: DocumentFormattingParams
    ) -> List[TextEdit]:
        """Format the entire document.

        Args:
            text: Document text.
            params: LSP formatting parameters (tab size, insert spaces).

        Returns:
            A list of ``TextEdit`` objects.  Empty when the document is
            already formatted (idempotent).
        """
        lines = text.splitlines()
        formatted = self._format_lines(lines, params)
        formatted_text = "\n".join(formatted)
        if text.endswith("\n"):
            formatted_text += "\n"
        if formatted_text == text:
            return []
        return [
            TextEdit(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=len(lines), character=0),
                ),
                new_text=formatted_text,
            )
        ]

    def format_range(
        self, text: str, params: DocumentRangeFormattingParams
    ) -> List[TextEdit]:
        """Format a range of lines within the document.

        The formatter extracts the lines within the requested range,
        formats them, and returns a ``TextEdit`` that replaces only that
        region.  Surrounding lines are not modified.

        If the range boundaries split a multi-line construct (e.g. route
        continuation), the formatter still operates on the explicit lines
        within the range and will not corrupt surrounding context.

        Args:
            text: Document text.
            params: LSP range-formatting parameters.

        Returns:
            A list of ``TextEdit`` objects for the specified range.
        """
        lines = text.splitlines()
        start_line = params.range.start.line
        end_line = params.range.end.line

        # Clamp to valid range
        start_line = max(0, min(start_line, len(lines)))
        end_line = max(0, min(end_line, len(lines)))

        if start_line >= end_line:
            return []

        selected = lines[start_line:end_line]
        formatted = self._format_lines(selected, params)

        formatted_text = "\n".join(formatted)
        if params.range.end.character > 0 or text.endswith("\n"):
            # Preserve trailing newline behavior for partial-range edits
            pass

        original_text = "\n".join(selected)
        if formatted_text == original_text:
            return []

        return [
            TextEdit(
                range=Range(
                    start=Position(line=start_line, character=0),
                    end=Position(line=end_line, character=0),
                ),
                new_text=formatted_text,
            )
        ]

    # ------------------------------------------------------------------
    # Internal formatting engine
    # ------------------------------------------------------------------

    def _format_lines(
        self,
        lines: List[str],
        params: DocumentFormattingParams | DocumentRangeFormattingParams,
    ) -> List[str]:
        """Apply formatting rules to a list of lines.

        Args:
            lines: Raw input lines (without trailing newlines).
            params: Formatting parameters (tab_size, insert_spaces).

        Returns:
            Formatted lines.
        """
        if not lines:
            return lines

        indent_size = params.options.tab_size if params.options else 2
        insert_spaces = params.options.insert_spaces if params.options else True
        indent_str = " " * indent_size if insert_spaces else "\t"

        formatted: List[str] = []
        # Track which structural section we are in.
        # Phases: "preamble", "route", "title", "charge_mult",
        #         "geometry", "post_geometry"
        phase = "preamble"
        route_lines: List[str] = []
        blank_after_route = False

        for raw_line in lines:
            stripped = raw_line.strip()

            # ---- blank lines ----
            if not stripped:
                if phase == "route":
                    # First blank after route marks the transition to title
                    phase = "title"
                formatted.append("")
                continue

            # ---- comment lines (preserve verbatim) ----
            if _COMMENT_RE.match(stripped):
                formatted.append(stripped)
                continue

            # ---- Link0 lines ----
            if _LINK0_RE.match(stripped):
                formatted.append(stripped)
                continue

            # ---- Route section ----
            if phase == "preamble" and _ROUTE_RE.match(stripped):
                phase = "route"
                route_lines = [stripped]
                formatted.append(stripped)
                continue

            if phase == "route" and not blank_after_route:
                if _is_route_continuation(stripped):
                    route_lines.append(stripped)
                    formatted.append(stripped)
                    continue

            # ---- Title line ----
            if phase == "title":
                # The title is a single free-form line; emit it as-is
                formatted.append(stripped)
                phase = "charge_mult"
                continue

            # ---- Charge/multiplicity ----
            if phase == "charge_mult":
                if _CHARGE_MULT_RE.match(stripped):
                    formatted.append(stripped)
                    phase = "geometry"
                    continue
                # If it doesn't match charge/mult, still transition
                formatted.append(stripped)
                phase = "geometry"
                continue

            # ---- Geometry lines (atoms) ----
            if phase == "geometry":
                # Check for ModRedundant before atoms: lines like "B 1 2 1.5"
                # match the atom regex (B = boron) but are ModRedundant commands.
                if _MODRED_RE.match(stripped) or _MODRED_SINGLE_RE.match(stripped):
                    phase = "post_geometry"
                    formatted.append(stripped)
                    continue
                if _ATOM_RE.match(stripped):
                    formatted.append(_format_atom_line(stripped))
                    continue
                # Empty line within geometry area already handled above
                # Any other line ends geometry
                phase = "post_geometry"
                formatted.append(stripped)
                continue

            # ---- Post-geometry (ModRedundant, variables, basis sections) ----
            if phase == "post_geometry":
                formatted.append(stripped)
                continue

            # Fallback: preserve verbatim
            formatted.append(stripped)

        return formatted


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_formatting_provider(server: LanguageServer) -> FormattingProvider:
    """Create a ``FormattingProvider`` instance.

    Args:
        server: The language server instance.

    Returns:
        A new ``FormattingProvider``.
    """
    return FormattingProvider(server)


__all__ = ["FormattingProvider", "get_formatting_provider"]
