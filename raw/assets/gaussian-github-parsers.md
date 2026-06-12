# Gaussian Input File Parsers and Utilities (GitHub)

> Sources:
> - https://github.com/cclib/cclib — Comprehensive computational chemistry parser
> - https://github.com/Sungil-Hong/gaussianutility — Gaussian 09/16 utilities
> - https://github.com/sinagilassi/GaussParse — Gaussian output parser to Excel/Word
> - https://github.com/team-mayes/gaussian_wrangler — Gaussian efficiency scripts
> - https://github.com/chunxiangzheng/gaussian_log_file_converter — Log to XYZ/GJF converter
> Fetched: 2026-06-12

## 1. cclib — The Standard Parser

**Repository:** https://github.com/cclib/cclib
**Parser:** `cclib/parser/gaussianparser.py`

The most comprehensive open-source Gaussian output parser. Parses:
- SCF energies and convergence
- Molecular orbitals (eigenvalues, symmetries)
- Geometries (optimized coordinates)
- Gradients and forces
- Vibrational frequencies and modes
- Thermochemistry (enthalpy, entropy, free energy)
- Dipole and higher multipole moments
- Atomic charges (Mulliken, Lowdin, etc.)
- Excitation energies (CIS, TD-DFT)
- NMR chemical shifts
- Mulliken and NBO population analysis

Key regex patterns from cclib for parsing Gaussian output:
- `gaussianparser.py` contains ~2000 lines of parsing logic
- Uses line-by-line scanning with state machines
- Handles multi-step jobs via `--Link1--` detection

## 2. gaussianutility

**Repository:** https://github.com/Sungil-Hong/gaussianutility

Python package for Gaussian 09/16 with:
- Input file parsing and manipulation
- ONIOM-type input/output handling
- Coordinate extraction
- File format conversion

## 3. GaussParse

**Repository:** https://github.com/sinagilassi/GaussParse

Python package for parsing Gaussian output to Excel/Word:
- Energy extraction
- Convergence analysis
- Geometry extraction

## 4. gaussian_wrangler

**Repository:** https://github.com/team-mayes/gaussian_wrangler

Scripts to improve efficiency and reproducibility:
- Input file generation
- Output parsing
- Batch processing utilities

## 5. gaussian_log_file_converter

**Repository:** https://github.com/chunxiangzheng/gaussian_log_file_converter

Converts Gaussian optimization output (.log) to XYZ or GJF format:
```bash
python extractOptimizedCoords.py input.log xyz|gjf
```

## Common Parsing Patterns from These Projects

### Route Section Detection
```
Route line starts with '#' (after optional whitespace)
Terminated by blank line
```

### Link0 Command Detection
```
Line starts with '%'
Known commands: Mem, Chk, OldChk, RWF, CPU, NProcShared, GPUCPU, etc.
```

### Multi-Step Job Detection
```
"--Link1--" separator between job steps
```

### Charge/Multiplicity
```
Line with two integers after title section blank line
Format: "charge multiplicity" (e.g., "0 1")
```

### Coordinate Section
After charge/multiplicity line:
- Cartesian: `Element X Y Z` or `AtomicNumber X Y Z`
- Z-matrix: `Element ref1 dist ref2 angle ref3 dihedral`
- Fragment markers for ONIOM: `Element X Y Z layer`

### Molecule Specification Terminators
- Blank line (for Cartesian)
- Blank line after variables section (for Z-matrix)
- `--Link1--` for multi-step jobs
