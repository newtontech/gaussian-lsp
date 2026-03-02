# Gaussian LSP

Language Server Protocol implementation for Gaussian quantum chemistry software.

## Features

- **Syntax highlighting** for `.gjf` and `.com` files
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

### VS Code Integration

Add to your VS Code settings:

```json
{
  "languageServerExample.trace.server": "verbose"
}
```

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
pytest tests/ --cov=src/gaussian_lsp --cov-report=html
```

### Code Quality

```bash
black src/ tests/
isort src/ tests/
mypy src/
flake8 src/ tests/
```

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

See [CHANGELOG.md](CHANGELOG.md) for version history.
