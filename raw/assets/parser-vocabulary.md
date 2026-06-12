---
source: src/gaussian_lsp/parser/gjf_parser.py (lines 14-364)
extracted: 2026-06-12
---

# Gaussian Parser Vocabulary

Structured vocabulary dump from the GJFParser. These lists define what the LSP recognizes.

## Methods (66 entries)

### Hartree-Fock
HF, RHF, UHF, ROHF

### DFT Functionals
B3LYP, B3P86, B3PW91, B1B95, B1LYP, PBE, PBE0, PBE1PBE, RPBE, revPBE, M06, M06HF, M062X, M06L, wB97, wB97X, wB97XD, CAM-B3LYP, BLYP, BP86, BP91, OLYP, OPBE, TPSS, TPSSH, revTPSS, BMK, VSXC, HSEH1PBE, OHSE2PBE, HCTH, MN12SX, MN12L, N12, N12SX, PW91PW91, PW91, mPW1PW91, mPW1LYP, mPW3PBE, X3LYP, XYG3, XYGJOS, LC-wPBE, LC-wPBEh, WB97X-D3, B2PLYPD, mPW2PLYPD

### Post-HF
MP2, MP3, MP4, MP4SDQ, MP5, CCSD, CCSD(T), QCISD, QCISD(T), CIS, CISD, EOM-CCSD

### Semi-empirical
PM3, PM6, PM7, AM1, RM1, MNDO, MNDOD, DFTB, DFTB3

## Basis Sets (82 entries)

### Pople
STO-3G, 3-21G, 3-21+G, 3-21++G, 3-21G*, 3-21+G*, 3-21++G*, 6-21G, 6-31G, 6-31+G, 6-31++G, 6-31G*, 6-31G(d), 6-31+G*, 6-31G**, 6-31G(d,p), 6-31+G**, 6-31++G**, 6-311G, 6-311+G, 6-311++G, 6-311G*, 6-311G(d), 6-311G**, 6-311G(d,p), 6-311+G**, 6-311++G(2d,2p), 6-311++G(3df,3pd)

### Dunning (Correlation-Consistent)
cc-pVDZ, cc-pVTZ, cc-pVQZ, cc-pV5Z, cc-pV6Z, aug-cc-pVDZ, aug-cc-pVTZ, aug-cc-pVQZ, aug-cc-pV5Z, cc-pCVDZ, cc-pCVTZ, cc-pCVQZ

### Karlsruhe (def2)
def2-SV(P), def2-SVP, def2-TZVP, def2-TZVPP, def2-QZVP, def2-QZVPP, def2-TZVPD, def2-TZVPPD, ma-def2-SVP, ma-def2-TZVP, ma-def2-TZVPP, ma-def2-QZVP, def2/J, def2-TZVP/J, def2-TZVPP/J

### Pseudopotentials / ECP
LANL2DZ, LANL2MB, SDD, cc-pVDZ-PP, cc-pVTZ-PP, cc-pVQZ-PP, def2-ECP, def2-SD

### Other
DGDZVP, DGDZVP2, PC-1, PC-2, PC-3, PC-4, SV, SVP, TZV, TZVP, QZVP, MINI, MIDI, D95, D95V, EPR-II, EPR-III, UGBS

## Job Types (31 entries)

SP, OPT, OPT FREQ, FREQ, RAMAN, POLAR, NMR, NMR=SpinSpin, TD, TD FREQ, CIS, CIS(D), POPT, FORCE, Scan, IRC, IRCMax, Stable, Volume, Density, Prop, COUNTERPOISE, Counterpoise, ONIOM, QM/MM, MM, ADMP, BOMD, MD, Polar, Polar=Numer

## Link0 Commands (19 entries)

chk, rwf, int, d2e, scr, lindaworkers, kjob, subst, mem, nproc, nprocs, nprocshared, nprocsshared, gpu, gpucards, pgmcards, oldchk, oldmatrix, oldraw, oldfc

## Valid Elements (120 entries)

Full periodic table (H through Og, 118 elements) plus dummy atoms: X, Bq
