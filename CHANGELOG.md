# Changelog

All notable changes to this project will be documented in this file.

## [0.2.3] - 2026-03-03

### Added
- Comprehensive documentation in docs/ directory
- Example input files (water.gjf, ethane.gjf, methane.com, transition_state.gjf)
- Additional test coverage tests (test_final_coverage.py, test_exact_branches.py)
- Total test count: 247 tests

### Enhanced
- Test coverage maintained at 97.34% (exceeds 93% requirement)
- Documentation completeness improved
- Example files showcase various calculation types

## [0.2.2] - 2026-03-03

### Added
- Final coverage test suite with 14 additional test cases
- Tests for ModRedundant detection edge cases
- Tests for route section without hash detection
- Tests for charge/multiplicity section handling
- Tests for server diagnostics on edge cases

### Enhanced
- Test coverage improved from 96.93% to 97.34%
- Total tests increased from 201 to 215
- All code quality checks passing

## [0.2.0] - 2026-03-02

### Added
- Complete periodic table support (118 elements up to Oganesson)
- `.com` file support in addition to `.gjf` files
- ModRedundant input section parsing
- ONIOM layer specification support
- Comprehensive keyword documentation for hover
- Extended validation with warnings and errors
- Code formatting feature
- Full test coverage for parser module
- Convenience functions: `parse_com()`, `parse_com_file()`, `validate_gjf()`

### Enhanced
- Improved LSP server with better diagnostics
- Expanded completion support for all Gaussian methods and basis sets
- Better error handling and validation
- Updated README with comprehensive documentation

## [0.1.0] - 2026-03-01

### Added
- Initial Gaussian LSP implementation
- Basic `.gjf` file parsing
- Syntax highlighting support
- Auto-completion for common keywords
- Basic diagnostics
- Initial test suite

## [0.2.1] - 2026-03-02

### Added
- Comprehensive test suite with 120 test cases
- Additional coverage tests for ModRedundant commands
- Edge case tests for diagnostics
- Server feature integration tests

### Enhanced
- Test coverage increased to 93 percent
- Improved validation error handling
- Better diagnostic coverage for edge cases
