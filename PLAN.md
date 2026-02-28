# ORCA LSP Development Plan

## Input File Format

### File Extensions
- `.inp` - ORCA input file

### Structure
```
! B3LYP def2-TZVP OPT FREQ
%maxcore 4000
%pal nprocs 4 end

* xyz 0 1
  O   0.000000   0.000000   0.000000
  H   0.757160   0.586260   0.000000
  H  -0.757160   0.586260   0.000000
*
```

### Simple Input Line (!)
- **Methods**: HF, DFT, MP2, CCSD(T), CASSCF
- **Basis Sets**: def2-SVP, def2-TZVP, def2-QZVP, cc-pVTZ
- **Job Types**: SP, OPT, FREQ, NUMFREQ, IRC, SCAN, MD

### % Blocks
- `%maxcore` - Memory per core (MB)
- `%pal` - Parallelization
- `%method` - Method details
- `%basis` - Basis set details
- `%scf` - SCF convergence
- `%geom` - Geometry optimization
- `%freq` - Frequency calculation
- `%md` - Molecular dynamics
- `%loc` - Localization
- `%plots` - Plot generation

## Implementation Phases

### Phase 1: Simple Input Parser (Week 1)
- [ ] Route line parser (!)
- [ ] Method detection
- [ ] Basis set detection
- [ ] Job type detection

### Phase 2: % Block Parser (Week 2)
- [ ] %maxcore parser
- [ ] %pal parser
- [ ] %method parser
- [ ] %basis parser
- [ ] %scf parser

### Phase 3: LSP Features (Week 3)
- [ ] Method completion
- [ ] Basis set completion
- [ ] Job type completion
- [ ] %block completion
- [ ] Error diagnostics

## Technical Details

### Parser Design
```python
class ORCAParser:
    def parse_simple_input(self, line: str) -> SimpleInput
    def parse_percent_block(self, text: str) -> PercentBlock
    def parse_geometry(self, text: str) -> Geometry
```

### Methods
- HF, DFT (B3LYP, PBE, PBE0, TPSS, M06, etc.)
- MP2, RI-MP2
- CCSD, CCSD(T), DLPNO-CCSD(T)
- CASSCF, NEVPT2

### Basis Sets
- Pople: 3-21G, 6-31G, 6-311G
- Karlsruhe: def2-SVP, def2-TZVP, def2-QZVP
- Dunning: cc-pVDZ, cc-pVTZ, cc-pVQZ
- Auxiliary: def2/J, def2-TZVP/C

### Diagnostics
- Invalid keywords
- Missing charge/multiplicity
- Basis set compatibility
- Memory settings

## Resources
- ORCA Manual
- ORCA Input Library
- ORCA Forum

---

*Plan Created: 2026-03-01*
*Target Completion: 3 weeks*
