"""Gaussian input file (.gjf) parser."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
    
    def to_gjf(self) -> str:
        """Convert job back to GJF format."""
        lines = []
        
        # Link0 section
        for key, value in self.link0.items():
            lines.append(f"%{key}={value}")
        if self.link0:
            lines.append("")
        
        # Route section
        lines.append(self.route_section)
        lines.append("")
        
        # Title
        lines.append(self.title)
        lines.append("")
        
        # Charge and multiplicity
        lines.append(f"{self.charge} {self.multiplicity}")
        
        # Atoms
        for atom in self.atoms:
            lines.append(f"{atom[0]:<2}  {atom[1]:>12.6f}  {atom[2]:>12.6f}  {atom[3]:>12.6f}")
        
        return "\n".join(lines)


class GJFParser:
    """Parser for Gaussian input files (.gjf)."""
    
    # Regular expressions for parsing
    LINK0_PATTERN = re.compile(r"^%(\w+)=(.+)$")
    CHARGE_MULT_PATTERN = re.compile(r"^(\d+)\s+(\d+)$")
    ATOM_PATTERN = re.compile(r"^(\w+)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)")
    
    def __init__(self):
        self.job = GaussianJob()
    
    def parse(self, content: str) -> GaussianJob:
        """
        Parse GJF content.
        
        Args:
            content: GJF file content as string
            
        Returns:
            GaussianJob object
        """
        lines = content.strip().split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        
        if not lines:
            raise ValueError("Empty GJF content")
        
        self.job = GaussianJob()
        section = "link0"
        
        for i, line in enumerate(lines):
            # Skip comments
            if line.startswith("!"):
                continue
            
            # Parse Link0 section (% keywords)
            if section == "link0":
                match = self.LINK0_PATTERN.match(line)
                if match:
                    key, value = match.groups()
                    self.job.link0[key] = value
                    continue
                else:
                    section = "route"
            
            # Parse route section
            if section == "route":
                if not line.startswith("#") and not line.startswith("%"):
                    section = "title"
                else:
                    if not self.job.route_section:
                        self.job.route_section = line
                    else:
                        self.job.route_section += " " + line
                    continue
            
            # Parse title
            if section == "title":
                if not self.job.title:
                    self.job.title = line
                    section = "charge_mult"
                    continue
            
            # Parse charge and multiplicity
            if section == "charge_mult":
                match = self.CHARGE_MULT_PATTERN.match(line)
                if match:
                    self.job.charge = int(match.group(1))
                    self.job.multiplicity = int(match.group(2))
                    section = "geometry"
                    continue
            
            # Parse geometry
            if section == "geometry":
                match = self.ATOM_PATTERN.match(line)
                if match:
                    element = match.group(1)
                    x = float(match.group(2))
                    y = float(match.group(3))
                    z = float(match.group(4))
                    self.job.atoms.append((element, x, y, z))
                elif line == "":
                    # End of geometry section
                    break
        
        return self.job
    
    def parse_file(self, filepath: str) -> GaussianJob:
        """
        Parse GJF file.
        
        Args:
            filepath: Path to GJF file
            
        Returns:
            GaussianJob object
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"GJF file not found: {filepath}")
        
        content = path.read_text()
        return self.parse(content)
    
    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate GJF content.
        
        Args:
            content: GJF file content
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        
        try:
            job = self.parse(content)
            
            if not job.route_section:
                errors.append("Missing route section")
            
            if not job.atoms:
                errors.append("No atoms defined in geometry section")
            
            # Validate atoms
            valid_elements = {
                "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
                "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
                "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
            }
            
            for atom in job.atoms:
                element = atom[0].capitalize()
                if element not in valid_elements:
                    errors.append(f"Unknown element: {atom[0]}")
        
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
        
        return len(errors) == 0, errors


def parse_gjf(content: str) -> GaussianJob:
    """
    Parse GJF content (convenience function).
    
    Args:
        content: GJF file content
        
    Returns:
        GaussianJob object
    """
    parser = GJFParser()
    return parser.parse(content)


def parse_gjf_file(filepath: str) -> GaussianJob:
    """
    Parse GJF file (convenience function).
    
    Args:
        filepath: Path to GJF file
        
    Returns:
        GaussianJob object
    """
    parser = GJFParser()
    return parser.parse_file(filepath)
