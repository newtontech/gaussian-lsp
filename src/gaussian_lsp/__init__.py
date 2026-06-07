"""Gaussian LSP package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gaussian-lsp")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.2.11"

from gaussian_lsp.parser import (
    GaussianJob,
    GJFParser,
    parse_com,
    parse_com_file,
    parse_gjf,
    parse_gjf_file,
    validate_gjf,
)

__all__ = [
    "__version__",
    "GJFParser",
    "GaussianJob",
    "parse_gjf",
    "parse_gjf_file",
    "parse_com",
    "parse_com_file",
    "validate_gjf",
]
