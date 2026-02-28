# Gaussian LSP Development Plan

## Input File Format

### File Extensions
- `.gjf` - Gaussian Job File
- `.com` - Command file
- `.inp` - Input file (generic)

### Structure
```
%chk=filename.chk          ← Link 0 commands (optional, %开头)
%mem=4GB
%nproc=4

# B3LYP/6-31G(d) opt freq  ← Route section (#开头)

Title line                 ← Title (blank line before/after)

0 1                        ← Charge and Multiplicity
H 0.0 0.0 0.0             ← Atom coordinates
O 0.0 0.0 0.96
H 0.93 0.0 -0.27

--Link1--                  ← Multiple jobs separator
```

### Route Section Keywords
**Methods**: HF, DFT (B3LYP, PBE0, M062X), MP2, CCSD(T), CASPT2
**Basis Sets**: STO-3G, 3-21G, 6-31G(d), 6-311++G(d,p), aug-cc-pVTZ
**Job Types**: SP, Opt, Freq, TD, IRC, Scan

## Implementation Phases

### Phase 1: Parser (Week 1)
- [ ] Route section parser
- [ ] Title section parser
- [ ] Charge/Multiplicity parser
- [ ] Geometry parser (Z-matrix and Cartesian)
- [ ] Link 0 commands parser

### Phase 2: LSP Features (Week 2)
- [ ] Syntax highlighting
- [ ] Route keyword completion
- [ ] Basis set completion
- [ ] Error diagnostics
- [ ] Hover documentation

### Phase 3: Advanced (Week 3)
- [ ] Quick Fixes for common errors
- [ ] Job type validation
- [ ] Resource estimation
- [ ] Output file linking

## Technical Details

### Parser Design
```python
class GaussianParser:
    def parse_route(self, line: str) -> RouteSection
    def parse_geometry(self, lines: List[str]) -> Geometry
    def parse_zmatrix(self, lines: List[str]) -> ZMatrix
```

### Completion Items
- 50+ computational methods
- 200+ basis sets
- 30+ job types
- Common keywords with descriptions

### Diagnostics
- Invalid route keywords
- Missing charge/multiplicity
- Geometry errors
- Unmatched parentheses in route

## Resources
- Gaussian User's Manual
- Gaussian Keyword Reference
- Computational Chemistry forums

---

*Plan Created: 2026-03-01*
*Target Completion: 3 weeks*
