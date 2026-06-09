"""Machine-readable code-intelligence API for AI coding agents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from lsprotocol.types import Diagnostic


@dataclass
class AgentAPISnapshot:
    uri: str = ""
    version: Optional[int] = None
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    outline: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({"uri": self.uri, "version": self.version,
            "diagnostics": self.diagnostics, "outline": self.outline,
            "metadata": self.metadata}, indent=2)


def _diag_to_dict(d: Diagnostic) -> Dict[str, Any]:
    return {"line": d.range.start.line, "character": d.range.start.character,
        "severity": d.severity, "message": d.message, "code": d.code, "source": d.source}


class AgentAPIProvider:
    def __init__(self) -> None:
        pass

    def get_snapshot(self, source: str, uri: str = "",
        version: Optional[int] = None, diagnostics: Optional[List[Diagnostic]] = None,
    ) -> AgentAPISnapshot:
        diag_dicts = [_diag_to_dict(d) for d in (diagnostics or [])]
        outline = self._build_outline(source)
        return AgentAPISnapshot(uri=uri, version=version,
            diagnostics=diag_dicts, outline=outline,
            metadata={"language": "gaussian", "provider": "gaussian_lsp",
                "feature_count": {"diagnostics": len(diag_dicts), "outline_items": len(outline)}})

    def _build_outline(self, source: str) -> List[Dict[str, Any]]:
        outline: List[Dict[str, Any]] = []
        lines = source.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("!") and not stripped.startswith("#"):
                outline.append({"line": i, "text": stripped[:80], "type": "content"})
        return outline

    def get_diagnostics_json(self, source: str, uri: str = "",
        diagnostics: Optional[List[Diagnostic]] = None) -> str:
        snap = self.get_snapshot(source, uri, diagnostics=diagnostics)
        return json.dumps({"uri": snap.uri, "diagnostics": snap.diagnostics, "count": len(snap.diagnostics)}, indent=2)

    def get_outline_json(self, source: str, uri: str = "") -> str:
        snap = self.get_snapshot(source, uri)
        return json.dumps({"uri": snap.uri, "outline": snap.outline}, indent=2)
