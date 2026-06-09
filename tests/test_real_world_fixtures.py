"""Regression tests for public real-world Gaussian input fixtures."""

from pathlib import Path

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "docs"


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "cctk_starting_structure.gjf",
            {
                "route_tokens": ("opt=modredundant", "b3lyp/6-31+g(d)", "scrf="),
                "title": "title",
                "charge": -1,
                "multiplicity": 1,
                "atom_count": 9,
                "link0": {"nprocshared": "16", "mem": "32GB"},
                "modredundant": ["B 1 7 F", "B 1 8 F"],
            },
        ),
        (
            "cctk_tutorial1.gjf",
            {
                "route_tokens": ("opt", "freq=noraman", "b3lyp/6-31g(d)"),
                "title": "title",
                "charge": 0,
                "multiplicity": 1,
                "atom_count": 15,
                "link0": {"mem": "32GB", "nprocshared": "16"},
            },
        ),
        (
            "openqc_water_opt.com",
            {
                "route_tokens": ("B3LYP/6-31G(d)", "opt", "freq"),
                "title": "Water molecule optimization",
                "charge": 0,
                "multiplicity": 1,
                "atom_count": 3,
                "link0": {"nprocshared": "8", "mem": "16GB", "chk": "water_opt.chk"},
            },
        ),
        (
            "qubekit_gaussian_gas_example.com",
            {
                "route_tokens": ("EmpiricalDispersion=GD3BJ", "b3lyp/6-311G", "OUTPUT=WFX"),
                "title": "gaussian job",
                "charge": 0,
                "multiplicity": 1,
                "atom_count": 3,
                "link0": {"mem": "1GB", "nprocshared": "1", "chk": "lig"},
            },
        ),
    ],
)
def test_parser_recognizes_public_gaussian_fixtures(filename, expected):
    """Public examples should continue to parse into the core GJF sections."""
    content = (FIXTURE_DIR / filename).read_text(encoding="utf-8")

    job = GJFParser().parse(content)

    assert job.route_section.startswith("#")
    for route_token in expected["route_tokens"]:
        assert route_token in job.route_section
    assert job.title == expected["title"]
    assert job.charge == expected["charge"]
    assert job.multiplicity == expected["multiplicity"]
    assert len(job.atoms) == expected["atom_count"]
    assert job.link0 == expected["link0"]

    if "modredundant" in expected:
        assert job.modredundant == expected["modredundant"]
