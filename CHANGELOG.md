
## [0.2.6] - 2026-03-04

### Added
- Additional test files: test_exact_branches.py, test_100_percent.py
- More comprehensive branch coverage tests
- Tests for exact line coverage targets

### Enhanced
- Test coverage maintained at 99% (323 tests passing)
- Parser module: 99% coverage (191 statements, 1 defensive line missing)
- Server module: 100% coverage (132 statements, 0 missing)
- All code quality checks passing (black, isort, mypy, flake8)

### Notes
- Remaining 1% coverage consists of 3 defensive code branches that are
  effectively unreachable in normal parsing scenarios:
  - Line 435->451: ModRedundant detection edge case after geometry section
  - Line 478: Route section append defensive check
  - Line 484->489: Charge/mult continue defensive check
