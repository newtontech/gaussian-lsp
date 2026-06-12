# Gaussian 16 Input File Format

> Source: https://gaussian.com/input/
> Fetched: 2026-06-12

## File Structure

Gaussian 16 input consists of a series of lines in an ASCII text file. The basic structure includes several sections:

1. **Link 0 Commands** — Locate and name scratch files (not blank-line terminated)
2. **Route section** (`#` lines) — Specify desired calculation type, model chemistry, and other options (blank-line terminated)
3. **Title section** — Brief description of the calculation (blank-line terminated; max 5 lines; not interpreted by program)
4. **Molecule specification** — Specify molecular system (blank-line terminated)
5. **Optional additional sections** — Additional input needed for specific job types (usually blank-line terminated)

Many Gaussian 16 jobs will include only sections 2, 3, and 4.

## Minimal Example: Single Point Energy on Water

```
#HF/6-31G(d)

water energy

0 1
O  -0.464  0.177  0.0
H  -0.464  1.137  0.0
H   0.441 -0.143  0.0
```

## Example with Link 0 Commands and Additional Sections

```
%Chk=heavy
#HF/6-31G(d) Opt=ModRedun

Opt job

0 1
atomic coordinates...
                    
3 8    Add a bond and an angle to the internal
2 1 3  coordinates used during the geom. opt.
```

## Multi-Step Input

```
%Chk=freq
# HF/6-31G(d) Freq

Frequencies at STP

Molecule specification

--Link1--
%Chk=freq
# HF/6-31G(d) SP

Frequencies at new temperature

Molecule specification
```

## Syntax Rules

- Input is **free-format** and **case-insensitive**
- Spaces, tabs, commas, or forward slashes can be used in any combination to separate items
- Multiple spaces are treated as a single delimiter

### Keyword Option Forms

- `keyword = option`
- `keyword(option)`
- `keyword=(option1, option2, ...)`
- `keyword(option1, option2, ...)`

Multiple options are enclosed in parentheses and separated by any valid delimiter. The equals sign before the opening parenthesis may be omitted.

Some options also take values; the option name is followed by an equals sign: e.g., `CBSExtrap(NMin=6)`

### Abbreviation

All keywords and options may be shortened to their **shortest unique abbreviation** within the entire Gaussian 16 system. Thus, `Conventional` may be abbreviated to `Conven`, but not to `Conv` (due to the presence of the `Convergence` option).

### File Inclusion

The contents of an external file may be included using `@filename`. Appending `/N` prevents echoing in output.

### Comments

Comments begin with an exclamation point (`!`), which may appear anywhere on a line. Separate comment lines may appear anywhere within the input file.

### Title Section Rules

- Cannot exceed **5 lines**
- Must be followed by a terminating blank line
- Characters to avoid: `@ # ! - _ \` and control characters (especially Ctrl-G)

## Route Section Prefixes

- `#` — Normal output level
- `#N` — Normal output (same as `#`)
- `#P` — Additional output (recommended for production jobs)
- `#T` — Terse output

## Section Ordering

The full ordering of possible sections in a Gaussian 16 input file is documented in the official "Section Ordering" page. The following keywords are associated with additional input sections:

- `Opt=ModRedundant` — Additional internal coordinates
- `Opt=Z-matrix` — Z-matrix variables
- `Gen` / `GenECP` — Custom basis set definitions
- `Guess=Alter` — Orbital alterations
- `Pop=ReadRadii` — Custom radii for population analysis
- `SCRF=Read` — Custom solvation parameters
- `Counterpoise` — Fragment definitions
- `NMR=Mixed` — Additional NMR parameters
