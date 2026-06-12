# Gaussian 16 Keywords Reference

> Sources:
> - https://gaussian.com/keywords/ — Complete keyword list
> - https://gaussian.com/capabilities/ — Methods, job types, links
> - https://wild.life.nctu.edu.tw/~jsyu/compchem/g09/g09ur/k_dft.htm — DFT functionals
> - https://gaussian.com/basissets/ — Basis sets
> - https://gaussian.com/scf/ — SCF keyword options
> - https://gaussian.com/link0/ — Link 0 commands
> Fetched: 2026-06-12

## Complete Gaussian 16 Keyword List

### A
- `ADMP` — Direct dynamics trajectory (Atom-centered Density Matrix Propagation)
- `#` — Route section initiator

### B
- `BD` — Brueckner Doubles
- `BOMD` — Born-Oppenheimer Molecular Dynamics

### C
- `CacheSize` — Set cache size for 2-electron integrals
- `CASSCF` — Complete Active Space SCF
- `CBS Methods` — Complete Basis Set methods (CBS-4M, CBS-QB3, CBS-APNO, etc.)
- `CBSExtrapolate` — Custom CBS extrapolation
- `CCD` / `CCSD` — Coupled cluster (doubles, singles+doubles)
- `Charge` — Set molecular charge
- `ChkBasis` — Read basis set from checkpoint file
- `CID` / `CISD` — Configuration Interaction (doubles, singles+doubles)
- `CIS` — Configuration Interaction Singles (excited states)
- `CNDO` — Complete Neglect of Differential Overlap (semi-empirical)

### D
- `Density` — Specify density for property calculation
- `DensityFit` / `NoDensityFit` — Density fitting for DFT
- `DFT Methods` — All DFT functionals (see separate section below)
- `DFTB` / `DFTBA` — Density Functional Tight Binding

### E
- `EET` — Excitation energy transfer
- `EOMCCSD` — Equation-of-Motion Coupled Cluster
- `EPT` — Electron Propagator Theory (electron affinities, ionization potentials)
- `EmpiricalDispersion` — Add empirical dispersion correction
- `External` — External calculation interface
- `ExtraBasis` / `ExtraDensityBasis` — Add extra basis functions

### F
- `Field` — Apply external electric field
- `FMM` — Fast Multipole Method
- `Force` — Compute forces on nuclei
- `Freq` — Frequency and thermochemical analysis

### G
- `Gen` / `GenECP` — General (user-specified) basis set input
- `GenChk` — Read general info from checkpoint
- `Geom` — Geometry input options
- `GFInput` — Print basis set in input format
- `GFPrint` — Print basis set in table format
- `Gn Methods` — Gn composite methods (G2, G3, G4, etc.)
- `Guess` — Initial guess for wavefunction
- `GVB` — Generalized Valence Bond

### H
- `HF` — Hartree-Fock (default method)

### I
- `INDO` — Intermediate Neglect of Differential Overlap
- `Integral` — Control integration grid and accuracy
- `IOp` — Internal Options (overlay/option=value)
- `IRC` — Intrinsic Reaction Coordinate
- `IRCMax` — Maximum energy along IRC

### K
- (no direct K keywords; keywords are listed alphabetically)

### L
- `Link0 Commands` — `%` prefixed commands (see Link0 section)
- `LSDA` — Local Spin Density Approximation (synonym for SVWN)

### M
- `MaxDisk` — Set maximum disk space
- `MINDO3` — Modified INDO version 3
- `MNDO` — Modified Neglect of Diatomic Overlap
- `MM Methods` — Molecular Mechanics (UFF, AMBER, DREIDING)
- `MP Methods` — Moller-Plesset perturbation theory (MP2, MP3, MP4, MP5)

### N
- `Name` — Rename the archive entry
- `NMR` — NMR shielding and chemical shifts

### O
- `ONIOM` — Our own N-layered Integrated molecular Orbital and molecular Mechanics
- `Opt` — Geometry optimization
- `Output` — Control output level

### P
- `PBC` — Periodic Boundary Conditions
- `Polar` — Polarizabilities and hyperpolarizabilities
- `Population` — Population analysis (Mulliken, NBO, etc.)
- `Pressure` — Set pressure for thermochemistry
- `Prop` — Compute molecular properties
- `Pseudo` — Read pseudopotentials
- `Punch` — Control punch file output

### Q
- `QCI` — Quadratic Configuration Interaction

### R
- `Restart` — Restart from checkpoint file

### S
- `SAC-CI` — Symmetry-Adapted Cluster CI
- `Scale` — Scale frequencies
- `Scan` — Potential energy surface scan
- `SCF` — SCF convergence control
- `SCRF` — Self-Consistent Reaction Field (solvation)
- `Semi-Empirical Methods` — AM1, PM3, PM6, etc.
- `SP` — Single point energy
- `Sparse` — Use sparse matrix algorithms
- `Stable` — Test wavefunction stability
- `Symmetry` — Control symmetry usage

### T
- `TD` — Time-Dependent (excited states via TD-DFT, TD-HF)
- `Temperature` — Set temperature for thermochemistry
- `Test` — Run test job
- `TestMO` — Test molecular orbitals
- `TrackIO` — Track I/O operations
- `Transformation` — MO transformation options

### U
- `Units` — Set coordinate units (Angstrom, Bohr)

### V
- `Volume` — Compute molecular volume

### W
- `W1 Methods` — W1U, W1BD, W1RO high-accuracy methods
- `Window` — Frozen core options

### Z
- `ZIndo` — Zerner's INDO (excited states)

## DFT Functionals Available in Gaussian 16

### Exchange Functionals

| Keyword | Description |
|---------|-------------|
| `S` | Slater exchange (LSD) |
| `XA` | XAlpha exchange |
| `B` | Becke 1988 |
| `PW91` | Perdew-Wang 1991 |
| `mPW` | Modified Perdew-Wang (Adamo-Barone) |
| `G96` | Gill 1996 |
| `PBE` | Perdew-Burke-Ernzerhof 1996 |
| `O` | Handy OPTX |
| `TPSS` | Tao-Perdew-Staroverov-Scuseria |
| `RevTPSS` | Revised TPSS |

### Correlation Functionals

| Keyword | Description |
|---------|-------------|
| `VWN` | Vosko-Wilk-Nusair (functional III) |
| `VWN5` | VWN functional V |
| `LYP` | Lee-Yang-Parr |
| `PL` | Perdew Local |
| `P86` | Perdew 1986 |
| `PW91` | Perdew-Wang 1991 |
| `B95` | Becke 95 (tau-dependent) |
| `PBE` | Perdew-Burke-Ernzerhof 1996 |
| `TPSS` | Tao-Perdew-Staroverov-Scuseria |

### Pure (Standalone) Functionals

| Keyword | Description |
|---------|-------------|
| `SVWN` / `LSDA` | Slater + VWN |
| `BLYP` | Becke88 + LYP |
| `BP86` | Becke88 + Perdew86 |
| `PBEPBE` | PBE exchange + correlation |
| `TPSSTPSS` | TPSS exchange + correlation |
| `VSXC` | van Voorhis-Scuseria |
| `HCTH` / `HCTH93` / `HCTH147` / `HCTH407` | Handy functionals |
| `M06L` | Truhlar pure functional |
| `B97D` / `B97D3` | B97 with Grimme dispersion |
| `SOGGA11` | Truhlar group functional |
| `M11L`, `MN12L`, `N12` | Truhlar group pure functionals |

### Hybrid Functionals

| Keyword | Description |
|---------|-------------|
| `B3LYP` | Becke 3-parameter hybrid (most popular) |
| `B3P86` | B3 with Perdew 86 correlation |
| `B3PW91` | B3 with PW91 correlation |
| `PBE1PBE` / `PBE0` | PBE hybrid (25% HF exchange) |
| `B1B95` | Becke 1-parameter hybrid |
| `mPW1PW91` | Modified PW hybrid |
| `B98` | Becke 1998 revision of B97 |
| `B971`, `B972` | Handy-Tozer modifications of B97 |
| `TPSSh` | TPSS hybrid |
| `BMK` | Boese-Martin tau-dependent |
| `M06`, `M06-2X`, `M06HF`, `M05`, `M05-2X` | Truhlar hybrids |
| `X3LYP` | Xu-Goddard functional |
| `APFD` | Austin-Frisch-Petersson with dispersion |
| `O3LYP` | OPTX-based 3-parameter |
| `SOGGA11X`, `M11`, `N12SX`, `MN12SX` | Truhlar hybrid functionals |

### Range-Separated / Long-Range Corrected Functionals

| Keyword | Description |
|---------|-------------|
| `wB97XD` | Head-Gordon with D2 dispersion |
| `wB97`, `wB97X` | Head-Gordon range-separated |
| `CAM-B3LYP` | Coulomb-attenuated B3LYP |
| `LC-wPBE` | Long-range corrected wPBE |
| `HSEH1PBE` / `HSE06` | Heyd-Scuseria-Ernzerhof |
| `OHSE2PBE` / `HSE03` | Earlier HSE form |
| `HISSbPBE` | HISS functional |

The prefix `LC-` may be added to any pure functional: e.g., `LC-BLYP`.

### Double-Hybrid Functionals (via MP2 keyword)

| Keyword | Description |
|---------|-------------|
| `B2PLYP` | Grimme double-hybrid |
| `B2PLYPD` / `B2PLYPD3` | With D2/D3 dispersion |
| `mPW2PLYPD` | Modified PW double-hybrid |

### Empirical Dispersion Options

```
EmpiricalDispersion=GD2    # Grimme D2
EmpiricalDispersion=GD3    # Grimme D3 original damping
EmpiricalDispersion=GD3BJ  # Grimme D3 with Becke-Johnson damping
EmpiricalDispersion=PFD    # Petersson-Frisch dispersion
```

## Basis Set Reference

### Pople-Style

| Keyword | Description |
|---------|-------------|
| `STO-3G` | Minimal basis (default) |
| `3-21G` | Split-valence |
| `6-21G` | Split-valence |
| `4-31G` | Split-valence |
| `6-31G` | Double-zeta split-valence |
| `6-311G` | Triple-zeta split-valence |

Polarization suffixes: `(d)`, `(d,p)`, `(2d)`, `(2d,2p)`, `(2df,2pd)`, `(3df,3pd)`
Diffuse: `+` (heavy atoms only), `++` (all atoms)
Shorthand: `*` = `(d)`, `**` = `(d,p)`

### Dunning Correlation-Consistent

| Keyword | Description |
|---------|-------------|
| `cc-pVDZ` | Double-zeta |
| `cc-pVTZ` | Triple-zeta |
| `cc-pVQZ` | Quadruple-zeta |
| `cc-pV5Z` | Quintuple-zeta |
| `cc-pV6Z` | Sextuple-zeta |
| `AUG-cc-pVDZ` | With diffuse functions |
| `AUG-cc-pVTZ` | With diffuse functions |

Truhlar "calendar" variants: `Jul-cc-pVDZ`, `Jun-cc-pVDZ`, `May-cc-pVDZ`, `Apr-cc-pVDZ`

### Ahlrichs / Karlsruhe

| Keyword | Description |
|---------|-------------|
| `Def2SVP` | Split-valence + polarization |
| `Def2TZVP` | Triple-zeta + polarization |
| `Def2TZVPP` | Triple-zeta + double polarization |
| `Def2QZVP` | Quadruple-zeta + polarization |
| `Def2QZVPP` | Quadruple-zeta + double polarization |

### Effective Core Potentials (ECPs)

| Keyword | Description |
|---------|-------------|
| `LanL2MB` | Los Alamos ECP + minimal basis |
| `LanL2DZ` | Los Alamos ECP + double-zeta |
| `SDD` | Stuttgart/Dresden ECPs |
| `SDDAll` | Stuttgart for all Z > 2 |
| `CEP-4G` | Stevens/Basch/Krauss minimal |
| `CEP-31G` | Stevens/Basch/Krauss split-valence |
| `CEP-121G` | Stevens/Basch/Krauss triple-split |

### Special-Purpose

| Keyword | Description |
|---------|-------------|
| `D95` / `D95V` | Dunning/Huzinaga double-zeta |
| `MidiX` | Truhlar MIDI! basis |
| `EPR-II` / `EPR-III` | Barone EPR basis sets |
| `UGBS` | Universal Gaussian basis set |
| `MTSmall` | Martin-de Oliveira (W1 method) |
| `DGDZVP` / `DGDZVP2` / `DGTZVP` | DGauss basis sets |
| `CBSB7` | CBS-QB3 basis (6-311G(2d,d,p)) |

## Link 0 Commands Reference

Link 0 commands are optional, precede the route section, and start with `%`.

| Command | Description |
|---------|-------------|
| `%Mem=N` | Dynamic memory (default 800 MB; suffixes: KB, MB, GB, TB) |
| `%Chk=file` | Checkpoint file location |
| `%OldChk=file` | Previous checkpoint file (read without modifying) |
| `%SChk=file` | Save copy of checkpoint file |
| `%RWF=file` | Read-write file location |
| `%RWF=loc1,size1,...` | Split RWF across multiple disks |
| `%OldMatrix=file` | Copy matrix element file to checkpoint |
| `%Int=spec` | Two-electron integral file location |
| `%D2E=spec` | Two-electron integral derivative file location |
| `%CPU=list` | Processor/core list for parallel jobs |
| `%NProcShared=N` | Number of shared-memory processors |
| `%GPUCPU=gpus=cores` | GPU-to-core pinning |
| `%LindaWorkers=nodes` | Network parallel nodes |
| `%KJob L N [M]` | Kill job after Mth occurrence of Link N |
| `%Save` | Save scratch files |
| `%ErrorSave` / `%NoSave` | Delete scratch on success |
| `%Subst L N dir` | Use alternate link executable |

## SCF Keyword Options

### Algorithm Selection

| Option | Description |
|--------|-------------|
| `DIIS` / `NoDIIS` | Enable/disable DIIS extrapolation |
| `CDIIS` | Classical DIIS (implies Damp) |
| `Fermi` | Temperature broadening (implies Damp) |
| `Damp` / `NoDamp` | Dynamic damping |
| `QC` | Quadratically convergent SCF |
| `XQC` | Try conventional first, fall back to QC |
| `YQC` | Large-molecule algorithm (SD + SCF + QC fallback) |
| `SD` | Steepest descent |
| `SSD` | Scaled steepest descent |
| `DM` | Direct minimization (legacy) |
| `MaxCycle=N` | Maximum SCF cycles (default 64) |
| `Conver=N` | Convergence to 10^-N |

### Integral Storage

| Option | Description |
|--------|-------------|
| `Direct` | Recompute integrals (default) |
| `InCore` | Store all integrals in memory |
| `Conventional` | Store integrals on disk |

### Symmetry

| Option | Description |
|--------|-------------|
| `NoSymm` | Lift all orbital symmetry constraints |
| `Symm` | Retain all symmetry constraints |
| `IDSymm` | Symmetrize density at first iteration |
| `DSymm` | Symmetrize density every iteration |

## Gaussian 16 Program Links

| Link | Function |
|------|----------|
| L0 | Initialize program |
| L1 | Process route section, build link list |
| L101 | Read title and molecule specification |
| L102 | Fletcher-Powell optimization |
| L103 | Berny optimization (minima, TS, STQN) |
| L202 | Reorient coordinates, calculate symmetry |
| L301 | Generate basis set info |
| L302 | Calculate integrals (overlap, kinetic, potential) |
| L401 | Form initial MO guess |
| L402 | Semi-empirical and MM calculations |
| L502 | SCF iteration (UHF, ROHF, direct, SCRF) |
| L503 | Direct minimization SCF |
| L508 | Quadratically convergent SCF |
| L601 | Population analysis (Mulliken, multipole) |
| L607 | NBO analysis |
| L701-703 | Integral derivatives |
| L716 | Process optimization and frequency info |
| L801-804 | Integral transformation |
| L902 | Wavefunction stability |
| L913 | Post-SCF energies and gradients |
| L914 | CIS/RPA excited states |
| L923 | SAC-CI |
| L1002 | CPHF equations |
| L9999 | Finalize calculation |

## Program Limits

- Max atoms: 250,000
- Max primitive shells: 750,000
- Max contracted shells: 250,000
- Max degree of contraction: 100
