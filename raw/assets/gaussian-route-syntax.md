# Gaussian 16 Route Section Syntax

> Source: https://gaussian.com/route/ (bot-blocked, reconstructed from input/, capabilities/, keywords/, and community docs)
> Also: https://gaussian.com/input/
> Fetched: 2026-06-12

## Route Section Basics

The route section of a Gaussian job is initiated by a **pound sign (#)** as the first non-blank character of a line. The remainder of the section is in **free-field format**.

### Output Level Specifiers

| Prefix | Meaning |
|--------|---------|
| `#` | Normal output (same as `#N`) |
| `#N` | Normal output |
| `#P` | Additional output (prints link timings, more detail) |
| `#T` | Terse output (minimal detail) |

### Termination

The route section is terminated by a **blank line**.

### Multi-Line Route Sections

The route section can span multiple lines; continuation is implicit (no special character needed). Example:

```
#p b3lyp/6-31+G(d,p) opt=(Z-Matrix) iop(1/7=30) int=ultrafine
EmpiricalDispersion=GD3
```

## Route Keyword Categories

Every Gaussian job must specify both a **method** and a **basis set** (unless using semi-empirical, MM, or compound methods). Keywords fall into these categories:

### 1. Method Keywords

Specify the level of theory:

| Category | Examples | Notes |
|----------|----------|-------|
| HF methods | `HF`, `RHF`, `UHF`, `ROHF` | Default if no method specified |
| DFT functionals | `B3LYP`, `BLYP`, `wB97XD`, `M06-2X`, `PBE1PBE` | ~50+ functionals |
| Post-HF | `MP2`, `MP3`, `MP4`, `CCSD`, `CCSD(T)`, `BD` | Include electron correlation |
| Semi-empirical | `AM1`, `PM3`, `PM6`, `MNDO`, `PM3MM` | No basis set needed |
| Compound methods | `CBS-QB3`, `G4`, `W1U`, `G2`, `G3` | No basis set needed |

Method prefixes: `R` (restricted), `U` (unrestricted), `RO` (restricted open-shell)
- Example: `UMP2`, `ROHF`, `RQCISD`
- `RO` available only for HF, DFT, semi-empirical energies/gradients, and MP2/MP3/MP4/CCSD energies

### 2. Basis Set Keywords

| Category | Examples | Notes |
|----------|----------|-------|
| Minimal | `STO-3G` | Default if no basis specified |
| Split-valence | `3-21G`, `6-31G`, `6-311G` | Pople-style |
| Polarization | `6-31G(d)`, `6-31G(d,p)`, `6-311G(2df,2p)` | Add `*` or `**` as shorthand |
| Diffuse | `6-31+G(d)`, `6-311++G(2d,p)` | `+` on heavy atoms, `++` on all |
| Dunning cc | `cc-pVDZ`, `cc-pVTZ`, `cc-pVQZ`, `cc-pV5Z` | With `AUG-` prefix for diffuse |
| Ahlrichs/def2 | `Def2SVP`, `Def2TZVP`, `Def2QZVP` | Karlsruhe basis sets |
| ECP | `LanL2DZ`, `SDD`, `CEP-121G` | Effective core potentials |

### 3. Job Type Keywords

| Keyword | Description |
|---------|-------------|
| `SP` | Single point energy (default) |
| `Opt` | Geometry optimization |
| `Freq` | Frequency and thermochemical analysis |
| `IRC` | Reaction path following |
| `IRCMax` | Maximum energy along reaction path |
| `Scan` | Potential energy surface scan |
| `Polar` | Polarizabilities and hyperpolarizabilities |
| `ADMP`, `BOMD` | Direct dynamics trajectory |
| `Force` | Compute forces on nuclei |
| `Stable` | Test wavefunction stability |
| `Volume` | Compute molecular volume |
| `TD` | Time-dependent (excited states) |
| `NMR` | NMR chemical shifts |
| `Pop` | Population analysis |

### 4. Option Keywords (modify behavior)

| Keyword | Description |
|---------|-------------|
| `SCF=...` | SCF convergence control |
| `Guess=...` | Initial guess method |
| `Geom=...` | Geometry input format |
| `Opt=...` | Optimization algorithm options |
| `Freq=...` | Frequency calculation options |
| `Integral=...` | Integration grid control |
| `Density=...` | Density matrix source |
| `Symmetry=...` | Symmetry handling |
| `IOp(N/M=K)` | Internal options |

## Compound Route Syntax

### Opt // Single Point

```
# CCSD/6-31G(d)//B3LYP/6-31G(d)
```
Requests B3LYP/6-31G(d) optimization followed by CCSD/6-31G(d) single point at optimized geometry.

### Combined Job Types

```
# B3LYP/6-31G(d) Opt Freq
```
Geometry optimization followed automatically by frequency calculation.

```
# B3LYP/6-31G(d) Polar Freq
```
Polarizability combined with frequency calculation.

## Keyword Option Syntax Examples

```
Opt=TS                    # Transition state optimization
Opt=(TS,ReadFC)           # TS opt reading force constants
Freq=Raman                # Include Raman intensities
SCF=(QC,MaxCycle=200)     # Quadratic SCF with 200 max cycles
SCF=(XQC,Conver=10)       # Extended QC with tight convergence
Integral=(UltraFine,Grid=5)  # Ultrafine integration grid
EmpiricalDispersion=GD3BJ # Grimme D3 with BJ damping
TD=(NStates=10,Root=1)   # TD-DFT: 10 states, root 1
```

## Common Route Section Patterns

### Basic DFT Optimization
```
# B3LYP/6-31G(d) Opt
```

### DFT with Dispersion and Tight Convergence
```
#P B3LYP/6-311+G(2d,p) Opt=Tight Int=UltraFine EmpiricalDispersion=GD3BJ
```

### HF Single Point
```
# HF/6-311+G(d,p) SP
```

### MP2 with Custom Basis
```
# MP2/Gen Freq
```

### High-Accuracy Compound Method
```
# CBS-QB3
```

### Transition State Search
```
# B3LYP/6-31G(d) Opt=(TS,NoEigenTest,CalcFC) Freq
```

### Solvent Effects (PCM)
```
# B3LYP/6-31G(d) Opt SCRF=(SMD,Solvent=Water)
```
