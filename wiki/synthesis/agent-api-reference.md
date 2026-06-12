# Agent API Reference

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：6

## 核心论点

gaussian-lsp 提供三层 agent-facing API：CLI 工具、Python AgentLSP 类、以及 LSP 自定义请求。所有 API 返回确定性 JSON，适合自动化回归和 agent 循环。

## CLI 接口

```bash
gaussian-lsp-tool <command> <path> [--format json]
```

| 命令 | 说明 | 输出 |
|------|------|------|
| `check` | 诊断输入文件 | 诊断列表 JSON |
| `context` | 位置上下文信息 | 上下文 JSON |
| `complete` | 补全建议 | 补全列表 JSON |
| `hover` | 悬停文档 | Markdown 文档 |
| `symbols` | 文档符号/大纲 | 符号树 JSON |
| `fix` | 修复建议 | 修复操作列表 |

## Python AgentLSP

```python
from gaussian_lsp.agent_lsp import AgentLSP

# 从文件创建
agent = AgentLSP.from_path("input.gjf")

# 从文本创建
agent = AgentLSP.from_text("%chk=test.chk\n# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nO 0 0 0\nH 0.75 0.58 0\nH -0.75 0.58 0")

# 运行诊断
result = agent.check()

# 获取位置上下文
context = agent.context(line=0, character=0)

# 获取补全
completions = agent.complete(line=0, character=2)

# 获取悬停信息
hover_info = agent.hover(line=0, character=2)

# 获取文档大纲
symbols = agent.symbols()
```

## Python AgentAPIProvider

```python
from gaussian_lsp.features.agent_api import AgentAPIProvider

provider = AgentAPIProvider()

# 获取诊断快照
snapshot = provider.get_snapshot(content)
# snapshot.uri, snapshot.version, snapshot.diagnostics, snapshot.outline, snapshot.metadata

# 获取诊断 JSON
diags_json = provider.get_diagnostics_json(content)

# 获取大纲 JSON
outline_json = provider.get_outline_json(content)
```

## AgentAPISnapshot 形状

```json
{
  "uri": "file:///path/to/input.gjf",
  "version": 1,
  "diagnostics": [
    {
      "code": "G001",
      "severity": "warning",
      "category": "schema",
      "confidence": 0.9,
      "source": "lint",
      "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
      "message": "Unknown route keyword"
    }
  ],
  "outline": [
    {"name": "Route", "kind": "module", "range": {...}},
    {"name": "Geometry", "kind": "class", "range": {...}}
  ],
  "metadata": {
    "software": "gaussian",
    "file_type": "input",
    "parser_version": "0.2.11"
  }
}
```

## LSP 自定义请求

| 请求 | 说明 |
|------|------|
| `Gaussian.diagnosticsSnapshot` | 返回诊断快照 JSON |

## 验证循环工作流

```
1. Agent 读取源文件
2. Agent 调用 diagnostics API (check / get_snapshot)
3. 如果有错误:
   a. Agent 分析错误消息
   b. Agent 应用修复
   c. Agent 重新请求诊断
4. 重复直到干净
```

### Golden Regression Harness

```python
from gaussian_lsp.features.regression import RegressionHarness

harness = RegressionHarness()
harness.add_fixture(GoldenFixture(
    name="basic_opt",
    input_source="# B3LYP/6-31G(d) opt\n\nWater\n\n0 1\nO 0 0 0\nH 0.75 0.58 0\nH -0.75 0.58 0",
    expected_diagnostics=[],
))
results = harness.run_all()
assert all(r.passed for r in results)
```

## 来源列表

- `src/gaussian_lsp/tool.py` — CLI 入口
- `src/gaussian_lsp/agent_lsp.py` — Python AgentLSP 类
- `src/gaussian_lsp/features/agent_api.py` — AgentAPIProvider
- `src/gaussian_lsp/features/diagnostic.py` — DiagnosticProvider
- `src/gaussian_lsp/features/regression.py` — RegressionHarness
- `docs/agent-verification-loop.md` — 验证循环文档
