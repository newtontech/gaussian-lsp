---
source: src/gaussian_lsp/server.py (KEYWORD_DOCS dict, lines 34-81)
extracted: 2026-06-12
---

# Gaussian LSP Keyword Documentation

Hover documentation strings from the server for methods, basis sets, and job types.

## Methods

- **HF**: Hartree-Fock method. Simplest ab initio using single Slater determinant.
- **RHF**: Restricted Hartree-Fock. For closed-shell systems.
- **UHF**: Unrestricted Hartree-Fock. Different orbitals for alpha/beta spins.
- **ROHF**: Restricted Open-shell Hartree-Fock. For open-shell systems.
- **MP2**: Moller-Plesset 2nd order perturbation. Includes electron correlation.
- **MP3**: Moller-Plesset third-order perturbation theory.
- **MP4**: Moller-Plesset fourth-order perturbation theory.
- **CCSD**: Coupled Cluster Singles and Doubles. High-level correlation method.
- **CCSD(T)**: CCSD with perturbative triples. Gold standard for QC.
- **B3LYP**: Becke 3-parameter, Lee-Yang-Parr hybrid DFT. Popular functional.
- **PBE**: Perdew-Burke-Ernzerhof gradient-corrected DFT functional.
- **PBE0**: Hybrid version of PBE with 25% exact exchange.
- **M06**: Minnesota 2006 functional. Good for transition metals.
- **M062X**: Minnesota 2006 functional with double hybrid. Main group chemistry.
- **wB97XD**: Long-range corrected hybrid functional with dispersion correction.
- **CAM-B3LYP**: Coulomb-attenuating B3LYP. Good for charge transfer.

## Basis Sets

- **STO-3G**: Minimal basis set. Fast but not accurate. Good for qualitative results.
- **3-21G**: Split-valence basis set. Better than minimal, still fast.
- **6-31G**: Split-valence basis set with 6 Gaussian primitives in core.
- **6-31G(d)**: 6-31G with polarization functions on heavy atoms.
- **6-31G(d,p)**: 6-31G with polarization functions on all atoms.
- **6-311G**: Triple-split valence basis set.
- **cc-pVDZ**: Correlation-consistent polarized valence double-zeta.
- **cc-pVTZ**: Correlation-consistent polarized valence triple-zeta.
- **cc-pVQZ**: Correlation-consistent polarized valence quadruple-zeta.
- **def2-SVP**: Karlsruhe split-valence basis set with polarization.
- **def2-TZVP**: Karlsruhe triple-zeta with polarization. Good balance.
- **def2-QZVP**: Karlsruhe quadruple-zeta basis set.
- **LANL2DZ**: LANL double-zeta with ECP for heavy elements.

## Job Types

- **SP**: Single point energy calculation.
- **OPT**: Geometry optimization. Finds local minimum energy structure.
- **FREQ**: Frequency calculation. Computes vibrational frequencies.
- **OPT FREQ**: Optimization + frequency. Verifies stationary point.
- **TS**: Transition state optimization. Searches for first-order saddle point.
- **IRC**: Intrinsic Reaction Coordinate. Follows reaction path from TS.
- **SCAN**: Potential energy surface scan.
- **RAMAN**: Raman activity calculation.
- **NMR**: NMR chemical shift calculation.
- **POLAR**: Polarizability and hyperpolarizability calculation.
- **TD**: Time-dependent DFT. For excited states.
- **CIS**: Configuration Interaction Singles. Excited state method.
- **COUNTERPOISE**: Counterpoise correction for basis set superposition error.
- **ONIOM**: N-layered Integrated molecular Orbital and Mechanics.
