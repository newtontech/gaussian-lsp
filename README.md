# Gaussian LSP

Language Server Protocol implementation for Gaussian quantum chemistry software.

## Features

- **Auto-completion** for Gaussian keywords (methods, basis sets, job types)
- **Diagnostics** with error and warning detection
- **Hover documentation** for Gaussian keywords
- **Code formatting** for consistent file structure
- Support for `.gjf` and `.com` input files
- Full periodic table support (118 elements)
- ModRedundant input support
- ONIOM layer specification support

## Installation

```bash
pip install gaussian-lsp
```

## Usage

Start the language server:

```bash
gaussian-lsp
```

### Editor Integration

This package provides the language server executable. To use it in an editor,
connect an LSP client to the `gaussian-lsp` command and register `.gjf` and
`.com` files as Gaussian input files. The repository does not currently ship a
VS Code extension or TextMate grammar.

Syntax highlighting depends on your editor or extension setup.

## OpenQC Alignment

This repository is part of the newtontech computational chemistry LSP family. `newtontech/OpenQC-VSCode` is the VS Code-facing integration layer for this server.

When changing diagnostics, completions, hover text, file detection, or parser fixtures, also update or open an alignment issue in `OpenQC-VSCode` so the extension behavior stays consistent with `gaussian-lsp`.

### Supported File Extensions

- `.gjf` - Gaussian input file
- `.com` - Gaussian command file

## Development

```bash
git clone https://github.com/newtontech/gaussian-lsp.git
cd gaussian-lsp
pip install -e ".[dev]"
```

### Running Tests

```bash
pip install -e ".[dev]"
python -m pytest
npm ci
npm run test:ts
```

The TypeScript parser under `src/parsers` is active and covered by
`npm run typecheck` plus `npm run test:ts:coverage` in CI.

If your local Python environment is not set up yet, you can reproduce the Python
suite without modifying the project environment:

```bash
uv run --with pytest --with pytest-asyncio --with pytest-cov python -m pytest
```

### Code Quality

```bash
black src/ tests/
isort src/ tests/
mypy src/
flake8 src/ tests/
pre-commit run --all-files
```

See `docs/pr-review-workflow.md` for the merge/modify/hold PR review process
and the parallel Codex subagent review lanes.

## Supported Keywords

### Methods
- Hartree-Fock: `HF`, `RHF`, `UHF`, `ROHF`
- DFT: `B3LYP`, `PBE`, `PBE0`, `M06`, `M062X`, `wB97XD`, etc.
- Post-HF: `MP2`, `MP3`, `MP4`, `CCSD`, `CCSD(T)`
- Semi-empirical: `PM3`, `PM6`, `PM7`, `AM1`

### Basis Sets
- Pople: `6-31G`, `6-31G(d)`, `6-311G(d,p)`, etc.
- Dunning: `cc-pVDZ`, `cc-pVTZ`, `cc-pVQZ`
- Karlsruhe: `def2-SVP`, `def2-TZVP`, `def2-QZVP`
- Pseudopotentials: `LANL2DZ`, `SDD`

### Job Types
- `SP` - Single point
- `OPT` - Geometry optimization
- `FREQ` - Frequency calculation
- `OPT FREQ` - Optimization + frequency
- `TS` - Transition state search
- `IRC` - Reaction coordinate
- `NMR` - NMR chemical shifts
- `TD` - Time-dependent DFT

## Example Input File

```
%chk=water.chk
%mem=2GB
%nproc=4

# B3LYP/6-31G(d) opt freq

Water molecule optimization

0 1
O  0.000000  0.000000  0.000000
H  0.757160  0.586260  0.000000
H -0.757160  0.586260  0.000000
```

## License

MIT

## Changelog

See [LICENSE](LICENSE) for the license text and [CHANGELOG.md](CHANGELOG.md)
for version history.
