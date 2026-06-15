#!/usr/bin/env bash
# OpenQC compatibility smoke test for gaussian-lsp
# Issue #80: lsp:check-family gate readiness
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXIT=0

echo "=== gaussian-lsp OpenQC Smoke Test ==="

# 1. Check lsp-capabilities.json exists and is valid
echo ""
echo "--- 1. lsp-capabilities.json ---"
if [ -f "$REPO_ROOT/lsp-capabilities.json" ]; then
    if python3 -m json.tool "$REPO_ROOT/lsp-capabilities.json" > /dev/null 2>&1; then
        echo "OK: lsp-capabilities.json is valid JSON"
    else
        echo "FAIL: lsp-capabilities.json is not valid JSON"
        EXIT=1
    fi
    # Check required fields
    HAS_OPENQC=$(python3 -c "import json; d=json.load(open('$REPO_ROOT/lsp-capabilities.json')); print('yes' if 'openqc' in d and d['openqc'].get('lsp_check_family') else 'no')")
    if [ "$HAS_OPENQC" = "yes" ]; then
        echo "OK: openqc.lsp_check_family = true"
    else
        echo "FAIL: openqc.lsp_check_family missing or false"
        EXIT=1
    fi
    HAS_PROVENANCE=$(python3 -c "import json; d=json.load(open('$REPO_ROOT/lsp-capabilities.json')); print('yes' if len(d.get('sourceProvenance', [])) > 0 else 'no')")
    if [ "$HAS_PROVENANCE" = "yes" ]; then
        echo "OK: sourceProvenance entries present"
    else
        echo "FAIL: sourceProvenance missing"
        EXIT=1
    fi
    HAS_CAPABILITIES=$(python3 -c "import json; d=json.load(open('$REPO_ROOT/lsp-capabilities.json')); caps=d.get('capabilities'); print('yes' if isinstance(caps, list) and len(caps) > 0 else 'no')")
    if [ "$HAS_CAPABILITIES" = "yes" ]; then
        echo "OK: capabilities section present"
    else
        echo "FAIL: capabilities section missing or empty"
        EXIT=1
    fi
else
    echo "FAIL: lsp-capabilities.json not found"
    EXIT=1
fi

# 2. Check raw/assets/manifest.json exists and is valid
echo ""
echo "--- 2. raw/assets/manifest.json ---"
if [ -f "$REPO_ROOT/raw/assets/manifest.json" ]; then
    if python3 -m json.tool "$REPO_ROOT/raw/assets/manifest.json" > /dev/null 2>&1; then
        echo "OK: manifest.json is valid JSON"
    else
        echo "FAIL: manifest.json is not valid JSON"
        EXIT=1
    fi
    ENTRY_COUNT=$(python3 -c "import json; d=json.load(open('$REPO_ROOT/raw/assets/manifest.json')); print(len(d.get('entries', [])))")
    echo "OK: manifest has $ENTRY_COUNT entries"
else
    echo "FAIL: raw/assets/manifest.json not found"
    EXIT=1
fi

# 3. Check fixtures exist
echo ""
echo "--- 3. Test fixtures ---"
for category in valid invalid log; do
    COUNT=$(find "$REPO_ROOT/tests/fixtures/$category" -type f 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        echo "OK: $category fixtures: $COUNT files"
    else
        echo "FAIL: no $category fixtures found"
        EXIT=1
    fi
done

# 4. Check source files
echo ""
echo "--- 4. Source files ---"
for f in src/gaussian_lsp/rich_diagnostics.py src/gaussian_lsp/tool.py src/gaussian_lsp/parser/gjf_parser.py; do
    if [ -f "$REPO_ROOT/$f" ]; then
        echo "OK: $f exists"
    else
        echo "FAIL: $f missing"
        EXIT=1
    fi
done

# 5. Summary
echo ""
echo "=== Summary ==="
if [ $EXIT -eq 0 ]; then
    echo "All checks PASSED"
else
    echo "Some checks FAILED"
fi
exit $EXIT
