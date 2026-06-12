# Plan: Apply LLM Wiki Pattern to gaussian-lsp

## Context

The gaussian-lsp project (`newtontech/gaussian-lsp`) has rich domain knowledge scattered across code, docs, and tests, but no structured knowledge base. Applying the Karpathy LLM Wiki pattern (via the `llm-wiki` skill) creates a browsable, source-grounded wiki that serves three audiences:

1. **Computational chemists** using the LSP in their editor
2. **Developers** contributing to gaussian-lsp
3. **AI agents** consuming the agent JSON API

The wiki uses `raw/` for source evidence, `wiki/` for agent-maintained synthesis, with Obsidian-style `[[Wiki_Link]]` cross-references.

## Directory Structure

```
gaussian-lsp/
  raw/
    assets/
  wiki/
    entities/
    concepts/
    synthesis/
  index.md
  log.md
```

## Implementation Phases

### Phase 1: Directory Structure + Raw Sources (7 files)

Create `raw/assets/` and populate with existing project artifacts as source evidence:

| File | Source |
|------|--------|
| `raw/assets/diagnostic-engine-v1.md` | `docs/DIAGNOSTIC_ENGINE_V1.md` |
| `raw/assets/agent-verification-loop.md` | `docs/agent-verification-loop.md` |
| `raw/assets/openqc-alignment.md` | `docs/OPENQC_ALIGNMENT.md` |
| `raw/assets/docs-overview.md` | `docs/docs.md` |
| `raw/assets/parser-vocabulary.md` | Extract from `src/gaussian_lsp/parser/gjf_parser.py` — all METHODS, BASIS_SETS, JOB_TYPES, LINK0_COMMANDS, VALID_ELEMENTS |
| `raw/assets/diagnostic-schema.md` | Summary from `diagnostics/diagnostic-engine-v1.schema.json` |
| `raw/assets/keyword-docs.md` | Extract KEYWORD_DOCS from `src/gaussian_lsp/server.py` |

### Phase 2: Entity Pages (8 files)

Foundation layer — concrete, nameable things in the Gaussian domain:

| Page | Covers |
|------|--------|
| `wiki/entities/hf-methods.md` | HF, RHF, UHF, ROHF — ab initio, closed/open-shell |
| `wiki/entities/dft-functionals.md` | B3LYP, PBE, PBE0, M06, wB97XD etc. — hybrid/meta-GGA/range-separated/GGA |
| `wiki/entities/post-hf-methods.md` | MP2, CCSD, CCSD(T) etc. — electron correlation, coupled cluster |
| `wiki/entities/basis-sets.md` | 70+ basis sets — Pople/Dunning/Karlsruhe/Pseudopotentials |
| `wiki/entities/job-types.md` | SP, OPT, FREQ, TS, IRC, NMR, TD etc. |
| `wiki/entities/link0-commands.md` | %chk, %mem, %nproc, %rwf, %gpu etc. — value types, validation |
| `wiki/entities/gaussian-input-format.md` | .gjf/.com structure, 118 elements, ModRedundant, ONIOM, Z-matrix |
| `wiki/entities/openqc-vscode.md` | OpenQC alignment, release check process |

### Phase 3: Concept Pages (6 files)

Cross-cutting concerns and reusable ideas:

| Page | Covers |
|------|--------|
| `wiki/concepts/route-section-syntax.md` | Route token parsing, method/basis separator, typo detection, SCF conflicts |
| `wiki/concepts/diagnostic-engine-v1.md` | Severity policy, 7 categories, rich diagnostic shape, confidence scoring |
| `wiki/concepts/open-shell-systems.md` | Multiplicity > 1, RHF/UHF/ROHF handling, Guess=Mix restrictions |
| `wiki/concepts/z-matrix-input.md` | Internal coordinates, variable definitions, definition/references/rename |
| `wiki/concepts/gen-basis-sections.md` | Gen/GenECP syntax, ECP block requirements, element cross-referencing |
| `wiki/concepts/scf-convergence.md` | SCF options (QC, DIIS, XQC), convergence levels, post-HF requirements |

### Phase 4: Synthesis Pages (5 files)

Top-level curated references:

| Page | Audience | Covers |
|------|----------|--------|
| `wiki/synthesis/diagnostics-rule-catalog.md` | All | Complete table: all G0xx-G3xx Python rules + TS rules + server implicit diagnostics, with code/severity/category/trigger/fix |
| `wiki/synthesis/agent-api-reference.md` | Agent/Dev | CLI surface, AgentLSP class, AgentAPIProvider, snapshot shape, verification loop |
| `wiki/synthesis/dsl-reference.md` | Chemist | Complete Gaussian input language: file structure, all vocabularies, syntax rules |
| `wiki/synthesis/provider-architecture.md` | Dev | Provider layer model, data flow, LSP registration, TypeScript parallel |
| `wiki/synthesis/development-workflow.md` | Dev | Setup, test commands, quality gates, issue workflow, PR review process |

### Phase 5: Navigation + Log (2 files)

| File | Purpose |
|------|---------|
| `index.md` | Navigation hub: quick start → entities → concepts → synthesis → raw sources |
| `log.md` | Initial entry documenting wiki creation date, scope, source coverage |

## Key Cross-References

Most-linked pages (build these first for referential integrity):
1. `[[Diagnostics_Rule_Catalog]]` — referenced from 6+ pages
2. `[[Diagnostic_Engine_V1]]` — referenced from 5+ pages
3. `[[Agent_API_Reference]]` — referenced from 4+ pages
4. `[[Gaussian_Input_Format]]` + `[[Route_Section_Syntax]]` — foundational

## Design Constraints

- **Bilingual**: Chinese headings where natural (类型, 简介, 关键属性), English technical terms preserved
- **Source-grounded**: Every page cites source file paths under "来源" section
- **No duplication**: Wiki synthesizes — does not copy README/CHANGELOG verbatim
- **`[[Wiki_Link]]` syntax** for all cross-references
- **Three audiences**: chemists (DSL ref, entities), developers (architecture, workflow), agents (API ref, diagnostics catalog)

## Critical Source Files

| File | Why |
|------|-----|
| `src/gaussian_lsp/parser/gjf_parser.py` | All vocabulary lists (methods, basis sets, job types, elements, Link0 commands) |
| `src/gaussian_lsp/server.py` | KEYWORD_DOCS, route semantic analysis, chemistry diagnostics |
| `src/gaussian_lsp/features/lint.py` | 10 stable lint rule codes (G001-G040) |
| `src/gaussian_lsp/rich_diagnostics.py` | Diagnostic Engine v1 serialization |
| `src/gaussian_lsp/features/agent_api.py` | Agent API provider |
| `docs/DIAGNOSTIC_ENGINE_V1.md` | Canonical diagnostic contract documentation |

## Verification

1. **Structure check**: `ls -R raw/ wiki/` confirms all directories and files exist
2. **Link check**: Grep all `[[...]]` references and verify target files exist
3. **Source traceability**: Every wiki page has a "来源" section with valid source paths
4. **Index completeness**: Every wiki page appears in `index.md`
5. **Log entry**: `log.md` has the initialization entry with date and scope
6. **No raw modification**: Files in `raw/` are verbatim copies or structured extracts, not rewritten
