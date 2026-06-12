# Gaussian 16 Output File Format

> Sources:
> - https://zipse.cup.uni-muenchen.de/teaching/computational-chemistry-2/topics/a-typical-gaussian-output-file/ — Detailed walkthrough
> - https://gaussian.com/opt/ — Output sections for optimization
> - https://github.com/cclib/cclib/blob/master/cclib/parser/gaussianparser.py — Parser reference
> - http://kisthelp.univ-reims.fr/userDocumentation/gaussian.html — KiSThelP parser sections
> Fetched: 2026-06-12

## Output File Structure

A Gaussian 16 output file is an ASCII text file with the following major sections:

### 1. Header / License Block

```
 Entering Gaussian System, Link 0=/scr1/g16/g16
 Initial command:
 /scr1/g16/l1.exe "/scr1/user/Gau-21572.inp" -scrdir="/scr1/user/"
 Entering Link 1 = /scr1/g16/l1.exe PID= 21576.
 Copyright (c) 1988,1990,...,2016,
 Gaussian, Inc.  All Rights Reserved.
 ...
 Cite this work as:
 Gaussian 16, Revision A.03,
 M. J. Frisch, G. W. Trucks, ... D. J. Fox,
 Gaussian, Inc., Wallingford CT, 2016.
```

### 2. Job Specification Block

```
 ******************************************
 Gaussian 16: ES64L-G16RevA.03 25-Dec-2016
 10-Mar-2020
 ******************************************
 %chk=/scr1/user/watdim01.chk
 %CPU=0-7
 Will use up to 8 processors via shared memory.
 %mem=16000MB
 ----------------------------------------------------------------------
 #p b3lyp/6-31+G(d,p) opt=(Z-Matrix) iop(1/7=30) int=ultrafine
 EmpiricalDispersion=GD3
 ----------------------------------------------------------------------
```

Key markers:
- Program version and revision
- Date of calculation
- Route section echoed (between `------` lines)
- Resource allocation (CPU, memory, checkpoint file)

### 3. Internal Settings (Link List)

```
 1/7=30,10=7,18=40,26=4,38=1/1,3;
 2/12=2,17=6,18=5,29=3,40=1/2;
 3/5=1,6=6,7=111,11=2,25=1,30=1,71=1,74=-5,75=-5,124=31/1,2,3;
 ...
```

This is the internal link sequence with IOp settings.

### 4. Title and Molecule Specification (L101)

```
 (Enter /scr1/g16/l101.exe)
 ----------------------------------------------------------------------
 watdim01 water dimer, B3LYP-D3/6-31+G(d,p) opt tight, Cs
 ----------------------------------------------------------------------
 Symbolic Z-matrix:
 Charge = 0 Multiplicity = 1
 O1
 H2 1 r2
 ...
 Variables:
 r2 0.9732
 ...
```

Key markers:
- `(Enter .../l101.exe)` — Link entry marker
- Title section echoed
- Charge and multiplicity
- Z-matrix or Cartesian coordinates
- NAtoms count

### 5. Optimization Initialization (L103) — for Opt jobs

```
 (Enter /scr1/g16/l103.exe)
 GradGradGradGradGradGradGradGradGradGradGradGradGradGradGradGradGradGrad
 Berny optimization.
 Initialization pass.
 ----------------------------
 !   Initial Parameters   !
 ! (Angstroms and Degrees) !
```

Key marker: `GradGradGrad...` border lines delimit optimization blocks.

### 6. Symmetry and Coordinate Processing (L202)

```
 (Enter /scr1/g16/l202.exe)
 Stoichiometry              H4O2
 Framework group            CS[SG(H2O2),X(H2)]
 Full point group           CS
 Standard orientation:
 ---------------------------------------------------------------------
 Center     Atomic     Atomic  Coordinates (Angstroms)
 Number     Number      Type   X        Y        Z
 ---------------------------------------------------------------------
```

Key markers:
- Stoichiometry
- Point group
- Standard orientation table
- Distance matrix

### 7. Basis Set Information (L301)

```
 (Enter /scr1/g16/l301.exe)
 Standard basis: 6-31+G(d,p) (6D, 7F)
 There are 41 symmetry adapted cartesian basis functions of A' symmetry.
 ...
 58 basis functions, 92 primitive gaussians, 58 cartesian basis functions
 10 alpha electrons   10 beta electrons
 nuclear repulsion energy   36.6574882778 Hartrees.
 IExCor=  402 DFT=T Ex+Corr=B3LYP
```

Key markers:
- Basis set name and size
- Number of basis functions and primitives
- Nuclear repulsion energy
- Method identification (IExCor, DFT settings)

### 8. Initial Guess (L401)

```
 Harris functional with IExCor= 402 diagonalized for initial guess.
 Initial guess orbital symmetries:
 Occupied  (A') (A') ...
 Virtual   (A') (A') ...
 The electronic state of the initial guess is 1-A'.
```

### 9. SCF Energy Calculation (L502) — THE CRITICAL SECTION

```
 (Enter /scr1/g16/l502.exe)
 Closed shell SCF:
 Requested convergence on RMS density matrix=1.00D-08 within 128 cycles.
 ...
 Cycle  1  Pass 0  IDiag  1:
 E= -152.743601726217
 ...
 SCF Done:  E(RB3LYP) =  -152.878894550  A.U. after  11 cycles
      NFock= 11  Conv=0.66D-08 -V/T= 2.0093
      KE= 1.514731736797D+02 PE=-4.339389047194D+02 EE= 9.293052597946D+01
```

**Key patterns to parse:**
- `SCF Done:  E(RB3LYP) =  -152.878894550  A.U. after  11 cycles`
  - Method label in parentheses: `RB3LYP`, `RHF`, `UB3LYP`, etc.
  - Energy in Hartree (atomic units)
  - Number of SCF cycles
- `Conver=` — convergence metric
- `-V/T=` — virial ratio

### 10. Population Analysis (L601)

```
 (Enter /scr1/g16/l601.exe)
 **********************************************************************
 Population analysis using the SCF density.
 **********************************************************************
 Orbital symmetries:
 ...
 Alpha occ. eigenvalues -- -19.19882 -19.13583 ...
 Alpha virt. eigenvalues --  0.00366  0.06676 ...
 The electronic state is 1-A'.
 Mulliken charges:
               1
  1  O   -0.763760
 ...
 Sum of Mulliken charges =  -0.00000
 Dipole moment (field-independent basis, Debye):
    X= -0.0631  Y= -3.0081  Z=  0.0000  Tot=  3.0088
```

Key markers:
- MO eigenvalues (energies in Hartree)
- Mulliken charges
- Dipole moment (in Debye)
- Higher multipole moments

### 11. Gradient / Force Calculation (L701-L703, L716)

```
 (Enter /scr1/g16/l716.exe)
 -------------------------------------------------------------------
 Center     Atomic              Forces (Hartrees/Bohr)
 Number     Number       X             Y             Z
 -------------------------------------------------------------------
    1          8      0.000091919    0.000000000    0.000035477
 ...
 Cartesian Forces:  Max     0.000107190 RMS     0.000048028
```

### 12. Optimization Step Summary (L103)

```
 Variable     Old X    -DE/DX    Delta X   Delta X   Delta X    New X
                        (Linear)  (Quad)    (Total)
 r2         1.83908   0.00002   0.00000   0.00003   0.00003   1.83912
 ...
 Item               Value     Threshold  Converged?
 Maximum Force       0.000144   0.000045   NO
 RMS     Force       0.000069   0.000030   NO
 Maximum Displacement 0.000696  0.000180   NO
 RMS     Displacement  0.000276  0.000120   NO
```

### 13. Optimization Completion

```
 Optimization completed.
    -- Stationary point found.
 ----------------------------
 !   Optimized Parameters   !
 ! (Angstroms and Degrees)  !
 ----------------------------
 !  Name  Definition    Value          Derivative Info.          !
 ! r2     R(1,2)        0.9732         -DE/DX =  0.0            !
 ...
```

### 14. Archive Entry (L9999)

```
 1\1\GINC-R1\FOpt\RB3LYP\6-31+G(d,p)\H4O2\ZIPSE\10-Mar-2020\1\\
 #p b3lyp/6-31+G(d,p) opt=(Z-Matrix) ...\\watdim01 water dimer...\\
 0,1\O\H,1,r2\H,1,r3,2,a3\...\\r2=0.97321674\r3=0.96405809\...\\
 Version=ES64L-G16RevA.03\State=1-A'\HF=-152.8788946\RMSD=7.843e-09\\
 Dipole=...\PG=CS [...]\\@
```

Key fields in archive entry:
- Job type (`FOpt` = Full Optimization)
- Method (`RB3LYP`)
- Basis set (`6-31+G(d,p)`)
- Stoichiometry (`H4O2`)
- `HF=` — Final energy in Hartree (misleading name; applies to all methods)
- `State=` — Electronic state
- `Dipole=` — Dipole moment
- `PG=` — Point group
- Coordinates and variables

### 15. Job Termination

```
 Normal termination of Gaussian 16 at Tue Mar 10 15:05:09 2020.
```

or

```
 Error termination via Lnk1e in /scr1/g16/l502.exe at Tue Mar 10 15:05:09 2020.
```

## Key Patterns for Output Parsing

| Pattern | Regex / Marker | Extracts |
|---------|----------------|----------|
| SCF Energy | `SCF Done:  E\((\w+)\) =\s+(-?\d+\.\d+)` | Method, energy |
| Normal termination | `Normal termination` | Job status |
| Error termination | `Error termination` | Job status |
| Optimization converged | `Optimization completed.` | Opt status |
| Stationary point | `Stationary point found.` | Opt result |
| Frequency | `Frequencies --\s+(\d+\.\d+)` | Vibrational frequencies |
| Charge & multiplicity | `Charge = (\d+) Multiplicity = (\d+)` | System state |
| NAtoms | `NAtoms=(\d+)` | System size |
| Archive energy | `HF=(-?\d+\.\d+)` | Final energy |
| Archive entry | `^\s*1\\1\\` | Complete job summary |
| Link entry | `\(Enter .*/l(\d+)\.exe\)` | Current link |
| Cycle count | `after\s+(\d+)\s+cycles` | SCF iterations |

## Energy Output Labels by Method

| Method | Output Label |
|--------|-------------|
| HF (restricted) | `E(RHF)` |
| HF (unrestricted) | `E(UHF)` |
| DFT B3LYP (restricted) | `E(RB+HF-LYP)` or `E(RB3LYP)` |
| MP2 | `EUMP2` or `E(MP2)` |
| CCSD | `E(CCSD)` |
| CCSD(T) | `E(CCSD(T))` |
