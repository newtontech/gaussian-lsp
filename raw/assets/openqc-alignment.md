---
source: docs/OPENQC_ALIGNMENT.md
extracted: 2026-06-12
---

# OpenQC Alignment

`gaussian-lsp` is the standalone Gaussian language server. `newtontech/OpenQC-VSCode` should expose the same language behavior in VS Code.

## Keep aligned

- File extensions: `.gjf`, `.com`.
- Diagnostics and severity levels for invalid routes, geometry blocks, ModRedundant sections, and ONIOM layers.
- Completion vocabulary for methods, basis sets, job types, and common keywords.
- Minimal parser fixtures used for smoke tests.

## Release check

Before a public OpenQC release, smoke test one valid and one invalid Gaussian input against this server and the extension.
