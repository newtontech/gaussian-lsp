## [Unreleased]

## [0.2.12] - 2026-07-16

### Added
- Tag-only PyPI trusted-publishing workflow using GitHub OIDC and the protected `pypi` environment.
- Fresh-wheel release smoke covering installed version metadata, server help/version, agent CLI, and valid, invalid, and runtime-log fixtures.
- OpenQC v1 docstring/wiki/raw traceability report (`reports/docstring-wiki-raw-traceability.json`) with schema `openqc.lsp.traceability.v1`, plus a deterministic generator/validator at `scripts/check_docstring_traceability.py` (#94). The report traces every diagnostic rule code constant from the Python lint provider, Python log parser, and TypeScript diagnostics surface through concrete wiki pages and raw evidence assets. `summary.docstringsLinked == summary.docstringsTotal`, and `brokenWikiLinks`, `wikiSourcesWithoutRaw`, and `rawManifestFailures` are all zero in strict mode.
- `docstring-traceability` capability in `lsp-capabilities.json` plus `openqc.traceability_report_entry` and `openqc.traceability_schema` pointers so the OpenQC family gate can discover the report.
- `CODE_INCOMPLETE_LOG = "GAUSS-I031"` constant in `src/gaussian_lsp/log_parser.py` so the truncated-log rule has a docstring symbol on par with the other GAUSS-Exx/Wxx codes; `log_manifest()` now advertises the code alongside `ALL_LOG_CODES`.
- `scripts/openqc_smoke.sh` checks the traceability report under section 5.
- `raw/assets/manifest.json` `wiki_links` rewritten to point at concrete files under `wiki/` so the manifest's own cross-artifact graph resolves.
- `VERSION` file and `release_provenance` metadata in `lsp-capabilities.json` for OpenQC provenance gates (#89)
- Python runtime log parser (`src/gaussian_lsp/log_parser.py`) closing the backend-only parity gap with the TypeScript `parseLog` surface (#87). Implements GAUSS-E034 (SCF convergence failure), GAUSS-E035 (geometry/Z-matrix parse failure), GAUSS-E036 (catch-all `Error termination via Lnk1e`), GAUSS-E037 (structured per-Link fault with role/cause/hint from the LINK_KNOWLEDGE table), GAUSS-E038 (optimization step budget exhausted), GAUSS-E039 (memory/disk exhaustion), GAUSS-W034 (per-iteration optimization convergence warning), and GAUSS-I031 (truncated/incomplete log marker). Every blocking finding carries an explicit `refusal_reason` explaining why the fix is unsafe to auto-apply.
- New `gaussian-lsp-tool parse-log` subcommand plus auto-detection in `gaussian-lsp-tool check`/`fix` for `.log`/`.out` files. `check` and `fix` route through the log parser when the file looks like a Gaussian runtime output.
- Realistic runtime log fixtures for SCF L502 failure (`error_termination_l502.log`), basis-set L301 failure (`error_termination_l301.log`), optimization exhaustion (`optimization_not_converged.log`), memory exhaustion (`memory_exhausted.log`), geometry/Z-matrix failure (`geometry_parse_failure.log`), clean run (`normal_termination.out`), and truncated log (`empty_truncated.log`) under `tests/fixtures/log/`.
- Rule-catalog fixtures for `GAUSS-E036`/`E037`/`E038`/`E039` under `tests/fixtures/rules/`.
- Wiki concept document `wiki/concepts/gaussian-log-runtime-errors.md` documenting the runtime-log capability, rule code mapping, and the Link knowledge table.
- Closed-loop fixture tests (`tests/test_closed_loop_fixtures.py`) for DiagnosticEnvelope/v1, fix previews, and OpenQC smoke evidence (#80).
- Lint cleanup in `tests/test_lsp_readiness.py` so `make check` passes on the maturity branch.

### Changed
- Aligned Python, TypeScript, VERSION, package, and OpenQC capability metadata for the 0.2.12 release.
- `gaussian-lsp-tool fix` now preserves first-party actions from diagnostics (log parser and preflight) and surfaces `refusal_reason` for every unsafe quickfix (#87).
- `lsp-capabilities.json` adds `runtime-log` capability, `parse-log` operation, log-parser source provenance, and the runtime-log codes in the diagnostic categories (#87).
- `wiki/synthesis/diagnostics-rule-catalog.md` documents the runtime-log capability with rule codes, Link knowledge table, and CLI examples.

### Fixed
- `scripts/openqc_smoke.sh` now checks real runtime modules instead of the removed `analyzer.py` stub.

## [0.2.11] - 2026-03-05

### Changed
- Code formatted with Black for consistent style
- All imports sorted with isort

### Quality
- 210/210 tests passing with 100% coverage
- All linting checks passing (black, isort, flake8)
- Type checking passing (mypy)
- Security checks passing (bandit)

## [0.2.8] - 2026-03-04

### Changed
- Updated version to 0.2.8
- Updated coverage requirement to 99% (from 93%)

### Added
- Additional test coverage: test_final_coverage.py
- Test cases for edge cases in parser

### Quality
- All 331 tests passing
- 99% code coverage maintained
- All linting and type checks passing

## [0.2.9] - 2026-03-05

### Changed
- Achieved **100% code coverage** (from 99%)
- Coverage requirement updated to 100% (from 99%)

### Added
- Final comprehensive test suite (337 tests total)
- test_100_coverage_final.py - Additional branch coverage tests
- test_smart_coverage.py - Smart edge case testing
- test_ultimate_coverage.py - Final edge case coverage

### Quality
- **337/337 tests passing (100%)**
- **100% code coverage achieved**
  - `__init__.py`: 100%
  - `parser/__init__.py`: 100%
  - `parser/gjf_parser.py`: 100%
  - `server.py`: 100%
- All linting and type checks passing
- Security checks passing (bandit)

### Notes
- Previous defensive code branches now covered
- All edge cases tested
- Production-ready release

## [0.2.10] - 2026-03-05

### Changed
- Cleaned up redundant test files, consolidated to 4 core test files
- Added defensive code annotations for unreachable branches

### Added
- test_edge_cases.py for edge case testing
- Additional diagnostic tests for empty files

### Quality
- 210/210 tests passing with 100% coverage
- All linting and type checks passing
