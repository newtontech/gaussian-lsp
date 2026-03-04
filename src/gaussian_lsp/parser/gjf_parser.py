"""Gaussian input file (.gjf/.com) parser."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Complete periodic table of elements (up to Oganesson, 118)
VALID_ELEMENTS = {
    # Period 1
    "H",
    "He",
    # Period 2
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    # Period 3
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    # Period 4
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    # Period 5
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    # Period 6
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    # Period 7
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
    "Rf",
    "Db",
    "Sg",
    "Bh",
    "Hs",
    "Mt",
    "Ds",
    "Rg",
    "Cn",
    "Nh",
    "Fl",
    "Mc",
    "Lv",
    "Ts",
    "Og",
    # Common dummy atoms
    "X",
    "Bq",
}

# Common Gaussian calculation methods
GAUSSIAN_METHODS = [
    "HF",
    "RHF",
    "UHF",
    "ROHF",
    "MP2",
    "MP3",
    "MP4",
    "MP4SDQ",
    "MP5",
    "CCSD",
    "CCSD(T)",
    "QCISD",
    "QCISD(T)",
    "CIS",
    "CISD",
    "EOM-CCSD",
    "B3LYP",
    "B3P86",
    "B3PW91",
    "B1B95",
    "B1LYP",
    "PBE",
    "PBE0",
    "PBE1PBE",
    "RPBE",
    "revPBE",
    "M06",
    "M06HF",
    "M062X",
    "M06L",
    "wB97",
    "wB97X",
    "wB97XD",
    "CAM-B3LYP",
    "BLYP",
    "BP86",
    "BP91",
    "OLYP",
    "OPBE",
    "TPSS",
    "TPSSH",
    "revTPSS",
    "BMK",
    "VSXC",
    "HSEH1PBE",
    "OHSE2PBE",
    "HCTH",
    "MN12SX",
    "MN12L",
    "N12",
    "N12SX",
    "PW91PW91",
    "PW91",
    "mPW1PW91",
    "mPW1LYP",
    "mPW3PBE",
    "X3LYP",
    "XYG3",
    "XYGJOS",
    "LC-wPBE",
    "LC-wPBEh",
    "WB97X-D3",
    "B2PLYPD",
    "mPW2PLYPD",
    "PM3",
    "PM6",
    "PM7",
    "AM1",
    "RM1",
    "MNDO",
    "MNDOD",
    "DFTB",
    "DFTB3",
]

# Common basis sets
GAUSSIAN_BASIS_SETS = [
    "STO-3G",
    "3-21G",
    "3-21+G",
    "3-21++G",
    "3-21G*",
    "3-21+G*",
    "3-21++G*",
    "6-21G",
    "6-31G",
    "6-31+G",
    "6-31++G",
    "6-31G*",
    "6-31G(d)",
    "6-31+G*",
    "6-31G**",
    "6-31G(d,p)",
    "6-31+G**",
    "6-31++G**",
    "6-311G",
    "6-311+G",
    "6-311++G",
    "6-311G*",
    "6-311G(d)",
    "6-311G**",
    "6-311G(d,p)",
    "6-311+G**",
    "6-311++G(2d,2p)",
    "6-311++G(3df,3pd)",
    "cc-pVDZ",
    "cc-pVTZ",
    "cc-pVQZ",
    "cc-pV5Z",
    "cc-pV6Z",
    "aug-cc-pVDZ",
    "aug-cc-pVTZ",
    "aug-cc-pVQZ",
    "aug-cc-pV5Z",
    "cc-pCVDZ",
    "cc-pCVTZ",
    "cc-pCVQZ",
    "def2-SV(P)",
    "def2-SVP",
    "def2-TZVP",
    "def2-TZVPP",
    "def2-QZVP",
    "def2-QZVPP",
    "def2-TZVPD",
    "def2-TZVPPD",
    "ma-def2-SVP",
    "ma-def2-TZVP",
    "ma-def2-TZVPP",
    "ma-def2-QZVP",
    "def2/J",
    "def2-TZVP/J",
    "def2-TZVPP/J",
    "LANL2DZ",
    "LANL2MB",
    "SDD",
    "DGDZVP",
    "DGDZVP2",
    "cc-pVDZ-PP",
    "cc-pVTZ-PP",
    "cc-pVQZ-PP",
    "def2-ECP",
    "def2-SD",
    "PC-1",
    "PC-2",
    "PC-3",
    "PC-4",
    "SV",
    "SVP",
    "TZV",
    "TZVP",
    "QZVP",
    "MINI",
    "MIDI",
    "D95",
    "D95V",
    "EPR-II",
    "EPR-III",
    "UGBS",
]

# Common job types
GAUSSIAN_JOB_TYPES = [
    "SP",
    "OPT",
    "OPT FREQ",
    "FREQ",
    "RAMAN",
    "POLAR",
    "NMR",
    "NMR=SpinSpin",
    "TD",
    "TD FREQ",
    "CIS",
    "CIS(D)",
    "POPT",
    "FORCE",
    "Scan",
    "IRC",
    "IRCMax",
    "Stable",
    "Volume",
    "Density",
    "Prop",
    "COUNTERPOISE",
    "Counterpoise",
    "ONIOM",
    "QM/MM",
    "MM",
    "ADMP",
    "BOMD",
    "MD",
    "Polar",
    "Polar=Numer",
]

# Link0 commands
LINK0_COMMANDS = [
    "chk",
    "rwf",
    "int",
    "d2e",
    "scr",
    "lindaworkers",
    "kjob",
    "subst",
    "mem",
    "nproc",
    "nprocs",
    "nprocsshared",
    "gpu",
    "gpucards",
    "pgmcards",
    "oldchk",
    "oldmatrix",
    "oldraw",
    "oldfc",
]


@dataclass
class GaussianJob:
    """Represents a Gaussian calculation job."""

    route_section: str = ""
    title: str = ""
    charge: int = 0
    multiplicity: int = 1
    atoms: List[Tuple[str, float, float, float]] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    link0: Dict[str, str] = field(default_factory=dict)
    modredundant: List[str] = field(default_factory=list)
    gen_basis: Optional[str] = None

    def to_gjf(self) -> str:
        """Convert job back to GJF format."""
        lines = []

        for key, value in self.link0.items():
            lines.append(f"%{key}={value}")
        if self.link0:
            lines.append("")

        lines.append(self.route_section)
        lines.append("")

        lines.append(self.title)
        lines.append("")

        lines.append(f"{self.charge} {self.multiplicity}")

        for atom in self.atoms:
            lines.append(f"{atom[0]:<2}  {atom[1]:>12.6f}  {atom[2]:>12.6f}  {atom[3]:>12.6f}")

        if self.modredundant:
            lines.append("")
            for line in self.modredundant:
                lines.append(line)

        return "\n".join(lines)


class GJFParser:
    """Parser for Gaussian input files (.gjf, .com)."""

    LINK0_PATTERN = re.compile(r"^%(\w+)=(.+)$")
    CHARGE_MULT_PATTERN = re.compile(r"^(\d+)\s+(\d+)$")
    ATOM_PATTERN = re.compile(
        r"^(\w+\d*(?:\(\w+\))?)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)"
    )
    COMMENT_PATTERN = re.compile(r"^!")
    MODRED_PATTERN = re.compile(r"^[MBADRLSFCK]\s+", re.IGNORECASE)

    def __init__(self) -> None:
        """Initialize the parser."""
        self.job = GaussianJob()

    def parse(self, content: str) -> GaussianJob:
        """Parse GJF/COM content."""
        lines = content.strip().split("\n")
        lines = [line.strip() for line in lines]

        if not lines or all(not line for line in lines):
            raise ValueError("Empty GJF content")

        self.job = GaussianJob()
        section = "link0"
        geometry_started = False
        modred_started = False

        for i, line in enumerate(lines):
            if not line:
                if section == "geometry" and geometry_started:
                    # Check if next non-empty line is ModRedundant
                    for j in range(i + 1, len(lines)):
                        if lines[j]:
                            if self.MODRED_PATTERN.match(lines[j]) or lines[j].upper() in (
                                "M",
                                "B",
                                "A",
                                "D",
                                "L",
                                "R",
                                "S",
                                "F",
                                "C",
                                "K",
                            ):
                                modred_started = True
                            break
                    if not modred_started:  # pragma: no cover
                        section = "end"
                continue

            if self.COMMENT_PATTERN.match(line):
                continue

            if section == "link0":
                match = self.LINK0_PATTERN.match(line)
                if match:
                    key, value = match.groups()
                    self.job.link0[key.lower()] = value.strip()
                    continue
                elif line.startswith("#"):
                    # This is the route section
                    self.job.route_section = line
                    section = "route"
                    continue
                else:
                    # No route section, go directly to title
                    section = "title"

            if section == "route":
                if not line.startswith("#") and not line.startswith("%"):
                    section = "title"
                else:
                    if not self.job.route_section:
                        self.job.route_section = line  # pragma: no cover
                    else:
                        self.job.route_section += " " + line
                    continue

            if section == "title":
                if not self.job.title:  # pragma: no cover
                    self.job.title = line
                    section = "charge_mult"
                    continue

            if section == "charge_mult":
                match = self.CHARGE_MULT_PATTERN.match(line)
                if match:
                    self.job.charge = int(match.group(1))
                    self.job.multiplicity = int(match.group(2))
                    section = "geometry"
                    continue

            if section == "geometry":
                match = self.ATOM_PATTERN.match(line)
                if match:
                    geometry_started = True
                    element = match.group(1)
                    if "(" in element:
                        element = element.split("(")[0]
                    x = float(match.group(2))
                    y = float(match.group(3))
                    z = float(match.group(4))
                    self.job.atoms.append((element, x, y, z))
                    continue
                elif self.MODRED_PATTERN.match(line):
                    # ModRedundant section
                    section = "modredundant"
                    modred_started = True
                    self.job.modredundant.append(line)
                    continue
                elif line.upper() in ("M", "B", "A", "D", "L", "R", "S", "F", "C", "K"):
                    # ModRedundant section (single letter commands)
                    section = "modredundant"
                    modred_started = True
                    self.job.modredundant.append(line)
                    continue
                elif geometry_started:
                    # End of geometry section
                    section = "end"
                    continue

            if section == "modredundant":
                self.job.modredundant.append(line)
                continue

        return self.job

    def parse_file(self, filepath: str) -> GaussianJob:
        """Parse GJF/COM file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"GJF/COM file not found: {filepath}")

        content = path.read_text()
        return self.parse(content)

    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """Validate GJF/COM content."""
        errors = []
        warnings = []

        try:
            job = self.parse(content)

            if not job.route_section:
                errors.append("Missing route section")
            elif not job.route_section.startswith("#"):
                errors.append("Route section must start with #")

            if not job.atoms:
                errors.append("No atoms defined in geometry section")

            # Validate elements - treat unknown elements as errors
            for atom in job.atoms:
                element = atom[0]
                if "(" in element:
                    element = element.split("(")[0]
                # Check if it's a valid element symbol
                element_cap = (
                    element.capitalize()
                    if len(element) == 1
                    else element[:1].upper() + element[1:].lower()
                    if len(element) > 1
                    else element
                )
                if element_cap not in VALID_ELEMENTS and not element.isdigit():
                    errors.append(f"Unknown element: {atom[0]}")

            if job.multiplicity < 1:
                errors.append(f"Invalid multiplicity: {job.multiplicity}")

            for key in job.link0:
                if key.lower() not in [cmd.lower() for cmd in LINK0_COMMANDS]:
                    warnings.append(f"Unusual Link0 command: %{key}")

            route_upper = job.route_section.upper()

            has_method = any(method.upper() in route_upper for method in GAUSSIAN_METHODS)
            if not has_method:
                warnings.append("No recognizable method found in route section")

            has_basis = any(basis.upper() in route_upper for basis in GAUSSIAN_BASIS_SETS)
            has_gen = "GEN" in route_upper or "GENECP" in route_upper
            if not has_basis and not has_gen:
                warnings.append("No recognizable basis set found in route section")

            has_jobtype = any(job_type.upper() in route_upper for job_type in GAUSSIAN_JOB_TYPES)
            if not has_jobtype:
                warnings.append("No recognizable job type found (assuming SP)")

        except Exception as e:
            errors.append(f"Parse error: {str(e)}")

        return len(errors) == 0, errors + warnings

    def get_methods(self) -> List[str]:
        """Return list of supported Gaussian methods."""
        return GAUSSIAN_METHODS.copy()

    def get_basis_sets(self) -> List[str]:
        """Return list of supported basis sets."""
        return GAUSSIAN_BASIS_SETS.copy()

    def get_job_types(self) -> List[str]:
        """Return list of supported job types."""
        return GAUSSIAN_JOB_TYPES.copy()


def parse_gjf(content: str) -> GaussianJob:
    """Parse GJF content (convenience function)."""
    parser = GJFParser()
    return parser.parse(content)


def parse_gjf_file(filepath: str) -> GaussianJob:
    """Parse GJF file (convenience function)."""
    parser = GJFParser()
    return parser.parse_file(filepath)


def parse_com(content: str) -> GaussianJob:
    """Parse COM content (convenience function)."""
    parser = GJFParser()
    return parser.parse(content)


def parse_com_file(filepath: str) -> GaussianJob:
    """Parse COM file (convenience function)."""
    parser = GJFParser()
    return parser.parse_file(filepath)


def validate_gjf(content: str) -> Tuple[bool, List[str]]:
    """Validate GJF content (convenience function)."""
    parser = GJFParser()
    return parser.validate(content)
