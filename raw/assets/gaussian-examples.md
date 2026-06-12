# Gaussian Input File Examples

> Sources:
> - https://gaussian.com/input/ — Official input format examples
> - https://emleddin.github.io/comp-chem-website/Otherguide-gaussian-input.html — Tutorial examples
> - https://github.com/Sungil-Hong/gaussianutility — Practical examples
> - https://zipse.cup.uni-muenchen.de/teaching/computational-chemistry-2/ — Water dimer example
> - Community examples from various compchem tutorials
> Fetched: 2026-06-12

## Example 1: HF Single Point Energy (Minimal)

```
#HF/6-31G(d)

water energy

0 1
O  -0.464  0.177  0.0
H  -0.464  1.137  0.0
H   0.441 -0.143  0.0

```

## Example 2: DFT Geometry Optimization with Checkpoint

```
%Chk=mol.chk
%Mem=8GB
%NProcShared=8
#P B3LYP/6-31G(d) Opt

Geometry optimization of methane

0 1
C     0.000000    0.000000    0.000000
H     0.000000    0.000000    1.089000
H     1.026719    0.000000   -0.363000
H    -0.513360   -0.889165   -0.363000
H    -0.513360    0.889165   -0.363000

```

## Example 3: DFT Optimization + Frequency with Dispersion

```
%Chk=water_dimer.chk
%Mem=16GB
%CPU=0-7
#P B3LYP/6-31+G(d,p) Opt=(Z-Matrix) Int=UltraFine EmpiricalDispersion=GD3

water dimer, B3LYP-D3/6-31+G(d,p) opt, Cs

0 1
O1
H2 1 r2
H3 1 r3 2 a3
X4 2 1. 1 90. 3 180. 0
O5 2 r5 4 a5 1 180. 0
H6 5 r6 2 a6 4 d6 0
H7 5 r6 2 a6 4 -d6 0

Variables:
r2 0.9732
r3 0.9641
r5 1.9128
r6 0.9659
a3 105.9
a5 83.1
a6 112.1
d6 59.6

```

## Example 4: Multi-Step Job (Freq then SP at different temperature)

```
%Chk=freq
# HF/6-31G(d) Freq

Frequencies at STP

0 1
O  0.0  0.0  0.0
H  0.0  0.0  0.96
H  0.96  0.0  0.0

--Link1--
%Chk=freq
# HF/6-31G(d) SP

Frequencies at new temperature

0 1
O  0.0  0.0  0.0
H  0.0  0.0  0.96
H  0.96  0.0  0.0

```

## Example 5: Geometry Optimization with ModRedundant

```
%Chk=heavy
# HF/6-31G(d) Opt=ModRedun

Opt job

0 1
atomic coordinates...

3 8
2 1 3

```

## Example 6: Transition State Search

```
%Chk=ts.chk
#P B3LYP/6-31G(d) Opt=(TS,NoEigenTest,CalcFC) Freq

Transition state for SN2 reaction

0 1
C   0.000  0.000  0.000
F   0.000  0.000  1.400
Cl  0.000  0.000 -2.000
H   1.000  0.000 -0.300
H  -0.500  0.866 -0.300
H  -0.500 -0.866 -0.300

```

## Example 7: TD-DFT Excited States

```
%Chk=td.chk
#P B3LYP/6-31+G(d,p) TD=(NStates=10,Root=1)

TD-DFT excited states calculation

0 1
formaldehyde coordinates...

```

## Example 8: NMR Chemical Shifts

```
%Chk=nmr.chk
#P B3LYP/6-311+G(2d,p) NMR=GIAO

NMR chemical shift calculation

0 1
molecule coordinates...

```

## Example 9: Solvation (PCM/SMD)

```
%Chk=solv.chk
#P B3LYP/6-31G(d) Opt SCRF=(SMD,Solvent=Water)

Optimization in water with SMD solvation

0 1
molecule coordinates...

```

## Example 10: MP2 Frequency with Custom Basis (Gen)

```
%Chk=mp2.chk
#P MP2/Gen Freq

MP2 frequency with custom basis

0 1
molecule coordinates...

C O 0
6-31G(d)
****
H 0
6-311G(d,p)
****

```

## Example 11: ONIOM Calculation

```
%Chk=oniom.chk
#P ONIOM(B3LYP/6-31G(d):HF/STO-3G) Opt

ONIOM optimization

0 1 0 1 0 1 0 1
[High layer atoms]   H H
[Medium layer atoms]  M M
[Low layer atoms]     L L

```

## Example 12: IRC Calculation

```
%Chk=irc.chk
#P B3LYP/6-31G(d) IRC=(MaxPoints=50,StepSize=10)

Intrinsic Reaction Coordinate

0 1
[TS geometry coordinates]

```

## Example 13: CBS-QB3 High Accuracy Energy

```
%Chk=cbs.chk
#P CBS-QB3

CBS-QB3 high accuracy energy

0 1
molecule coordinates...

```

## Example 14: PES Scan

```
%Chk=scan.chk
#P B3LYP/6-31G(d) Scan

Potential energy surface scan

0 1
O1
H2 1 r2
H3 1 r3 2 a3

r2=0.9 10 0.05
r3=0.96
a3=104.5

```

## Example 15: CASSCF Calculation

```
%Chk=casscf.chk
#P CASSCF(6,6)/6-31G(d) Opt

CASSCF(6,6) optimization

0 1
molecule coordinates...

```

## File Extension Conventions

| Extension | Usage |
|-----------|-------|
| `.gjf` | Gaussian Job File (common Windows convention) |
| `.com` | Gaussian input file (common UNIX convention) |
| `.chk` | Binary checkpoint file |
| `.log` | Output log file |
| `.rwf` | Read-write scratch file |
