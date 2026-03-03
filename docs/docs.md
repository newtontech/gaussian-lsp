# Gaussian LSP Documentation

## Overview

Gaussian-LSP is a Language Server Protocol (LSP) implementation for Gaussian quantum chemistry input files (.gjf and .com).

## Features

### 1. Syntax Highlighting
- Full support for `.gjf` and `.com` file extensions
- Recognition of Gaussian keywords, methods, and basis sets

### 2. Auto-completion
- **Methods**: HF, DFT (B3LYP, PBE, M06, etc.), Post-HF (MP2, CCSD, etc.)
- **Basis Sets**: Pople, Dunning, Karlsruhe, Pseudopotentials
- **Job Types**: SP, OPT, FREQ, TS, IRC, NMR, TD, etc.

### 3. Diagnostics
- Missing route section detection
- Invalid element symbols
- Missing atoms in geometry
- Method/basis set validation
- Multiplicity validation

### 4. Hover Documentation
- Detailed descriptions for methods, basis sets, and job types
- Context-aware documentation

### 5. Code Formatting
- Automatic formatting of GJF files
- Consistent structure and spacing

## File Structure

### Gaussian Input File Format

```
%Link0 commands (optional)
%chk=filename.chk
%mem=2GB
%nproc=4

# Route section (required)
# Method/BasisSet JobType

Title (required)

Charge Multiplicity (required)
Atom X Y Z
...

[ModRedundant section] (optional)
```

### Sections

1. **Link0 Section** (optional): System settings
   - `%chk` - Checkpoint file
   - `%mem` - Memory allocation
   - `%nproc` - Number of processors

2. **Route Section** (required): Calculation specifications
   - Must start with `#`
   - Contains method, basis set, and job type

3. **Title Section** (required): Description of calculation

4. **Molecule Specification** (required):
   - Charge and multiplicity line
   - Atomic coordinates

5. **ModRedundant** (optional): Coordinate modifications

## Supported Elements

Full periodic table support (118 elements):
- H to Og (Oganesson)
- Dummy atoms: X, Bq

## Supported Methods

### Hartree-Fock
- HF, RHF, UHF, ROHF

### DFT Functionals
- B3LYP, PBE, PBE0, M06, M062X, wB97XD
- CAM-B3LYP, BLYP, BP86, TPSS, etc.

### Post-HF Methods
- MP2, MP3, MP4, CCSD, CCSD(T)
- QCISD, CIS, CISD

### Semi-empirical
- PM3, PM6, PM7, AM1, RM1

## Supported Basis Sets

### Pople Style
- STO-3G, 3-21G, 6-31G, 6-311G
- Polarization: (d), (d,p), ++, etc.

### Correlation Consistent
- cc-pVDZ, cc-pVTZ, cc-pVQZ, cc-pV5Z
- aug-cc-pVDZ, etc.

### Karlsruhe
- def2-SVP, def2-TZVP, def2-QZVP

### Pseudopotentials
- LANL2DZ, SDD, def2-ECP

## Usage Examples

### Basic Single Point
```
# B3LYP/6-31G(d)

Water molecule

0 1
O  0.000000  0.000000  0.000000
H  0.757160  0.586260  0.000000
H -0.757160  0.586260  0.000000
```

### Optimization + Frequency
```
%chk=ethane.chk
%mem=4GB
%nproc=8

# B3LYP/6-311G(d,p) opt freq

Ethane optimization

0 1
C  0.000000  0.000000  0.000000
C  1.540000  0.000000  0.000000
H -0.540000  0.940000  0.000000
...
```

### Transition State
```
# B3LYP/6-31G(d) opt=(ts,calcfc)

TS search

0 1
...
```

### ONIOM
```
# ONIOM(B3LYP/6-31G(d):PM6)

ONIOM calculation

0 1
C(High)  0.0  0.0  0.0
H(Low)   1.0  0.0  0.0
...
```

## Development

### Setup
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

## Configuration

### VS Code
Add to settings.json:
```json
{
  "languageServerExample.trace.server": "verbose"
}
```

## Troubleshooting

### Common Issues

1. **Route section not recognized**
   - Ensure route section starts with `#`
   - Check for proper formatting

2. **Unknown element errors**
   - Use standard element symbols
   - Check capitalization (e.g., "Fe" not "FE")

3. **Missing geometry**
   - Ensure atoms are defined after charge/multiplicity
   - Check coordinate format

## License

MIT License - See LICENSE file for details.
