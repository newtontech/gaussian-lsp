---
source: diagnostics/diagnostic-engine-v1.schema.json
extracted: 2026-06-12
---

# Diagnostic Engine v1 JSON Schema

Rendered summary of the rich diagnostic contract.

## Schema: Diagnostic Engine v1 Rich Diagnostic

**Type**: object
**ID**: https://newtontech.local/schemas/diagnostic-engine-v1.json

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Stable diagnostic rule code (e.g., G001, GAUSS-E030) |
| `severity` | enum | One of: `error`, `warning`, `information`, `hint` |
| `category` | enum | One of: `syntax`, `schema`, `type/value`, `cross-file reference`, `semantic consistency`, `preflight/runtime-risk`, `style/deprecation` |
| `confidence` | number | 0.0 to 1.0 — how certain the diagnostic is |
| `source` | string | Provider identifier (e.g., "gaussian-lsp") |
| `range` | object | `start` and `end`, each with `line` (int ≥ 0) and `character` (int ≥ 0) |
| `software` | string | Target software (e.g., "gaussian") |
| `file_type` | string | File type tag (e.g., "input") |
| `path` | string | File path or identifier |
| `fix_hints` | array | List of suggested fixes |
| `blocking` | boolean | Whether this diagnostic should block automated submission |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `expected` | any | Expected value for type/value diagnostics |
| `actual` | any | Actual value found |
| `manual_ref` | string or null | Reference to upstream documentation |

### Severity Semantics

- **error**: High-confidence issue that should block submission. The upstream runtime will likely reject the input.
- **warning**: High-risk or suspicious input. May be intentional. Show to agents without auto-blocking.
- **information**: Style or documentation note.
- **hint**: Optional optimization suggestion.

### Category Semantics

- **syntax**: Malformed input structure
- **schema**: Missing required sections or invalid section ordering
- **type/value**: Incorrect value types or out-of-range values
- **cross-file reference**: Invalid file references (checkpoint, basis file, etc.)
- **semantic consistency**: Chemically or logically inconsistent input
- **preflight/runtime-risk**: Likely to cause runtime failure or excessive resource usage
- **style/deprecation**: Non-idiomatic usage or deprecated features
