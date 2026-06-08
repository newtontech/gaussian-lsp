"""LSP diagnostic provider for Gaussian input files."""

from __future__ import annotations

import json
from typing import Any

from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)
from pygls.server import LanguageServer


class DiagnosticProvider:
    """Provider for Gaussian diagnostics.

    Wraps the existing server-level analysis logic so it can be called
    from LSP lifecycle handlers (did_open, did_change) and also from
    CLI / automation scripts that need deterministic, JSON-serializable
    diagnostic snapshots.
    """

    def __init__(self, server: LanguageServer) -> None:
        """Initialize diagnostic provider.

        Args:
            server: The language server instance.
        """
        self.server = server

    def get_diagnostics(self, text: str) -> list[Diagnostic]:
        """Get diagnostics for the document text.

        Delegates to the server-level ``_analyze_content`` function so
        that the provider stays consistent with the pull-diagnostics
        handler.

        Args:
            text: Document text.

        Returns:
            List of LSP Diagnostic objects.
        """
        # Import here to avoid circular imports at module level.
        from gaussian_lsp.server import _analyze_content

        return _analyze_content(text)

    def get_diagnostics_snapshot(self, text: str) -> list[dict[str, Any]]:
        """Return a JSON-serializable diagnostic snapshot.

        Each diagnostic is represented as a deterministic dictionary
        with keys: ``uri``, ``range`` (start/end line+character),
        ``severity``, ``source``, ``message``, and ``code``.

        The result is sorted by (line, character, severity) so that
        repeated calls on the same input produce identical output.

        Args:
            text: Document text.

        Returns:
            A list of plain dicts suitable for ``json.dumps``.
        """
        diagnostics = self.get_diagnostics(text)
        return self._serialize_diagnostics(diagnostics)

    @staticmethod
    def _serialize_diagnostics(
        diagnostics: list[Diagnostic],
    ) -> list[dict[str, Any]]:
        """Convert LSP Diagnostic objects to deterministic dicts.

        Args:
            diagnostics: LSP diagnostics to serialize.

        Returns:
            JSON-serializable list of dicts.
        """
        snapshot: list[dict[str, Any]] = []
        for diag in diagnostics:
            severity_name = _severity_name(diag.severity)
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
                "severity": severity_name,
                "source": diag.source or "gaussian-lsp",
                "message": diag.message,
            }
            if diag.code is not None:
                entry["code"] = diag.code
            snapshot.append(entry)

        # Deterministic ordering: line, then character, then severity rank.
        severity_order = {"error": 0, "warning": 1, "information": 2, "hint": 3}
        snapshot.sort(
            key=lambda d: (
                d["range"]["start"]["line"],
                d["range"]["start"]["character"],
                severity_order.get(d["severity"], 4),
            )
        )
        return snapshot


def _severity_name(severity: int | None) -> str:
    """Map numeric severity to a stable string label.

    Args:
        severity: LSP DiagnosticSeverity value.

    Returns:
        Human-readable severity name.
    """
    mapping = {
        DiagnosticSeverity.Error: "error",
        DiagnosticSeverity.Warning: "warning",
        DiagnosticSeverity.Information: "information",
        DiagnosticSeverity.Hint: "hint",
    }
    if severity is None:
        return "error"
    return mapping.get(severity, "error")


__all__ = ["DiagnosticProvider"]
