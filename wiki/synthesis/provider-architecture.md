# Provider Architecture

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：6

## 核心论点

gaussian-lsp 采用分层 Provider 架构，每个 LSP 功能由独立的 Provider 类实现。诊断数据从原始文本流经 GJFParser → GaussianJob → 多个诊断函数 → LSP Diagnostic → 可选 rich diagnostic 序列化。

## Provider 层次

```
原始文本
  │
  ▼
GJFParser.parse() ──→ GaussianJob (AST)
  │
  ├── DiagnosticProvider ──→ 基础结构诊断
  ├── LintProvider ──→ G0xx-G3xx lint 规则
  ├── TypecheckProvider ──→ 关键词类型/枚举/单位验证
  ├── CodeActionProvider ──→ 修复建议
  │
  ▼
List[LSP Diagnostic]
  │
  ▼
rich_diagnostics.diagnostic_to_dict() ──→ Agent JSON
```

### Provider 详解

| Provider | 源文件 | source 标识 | 职责 |
|----------|--------|-------------|------|
| **DiagnosticProvider** | `features/diagnostic.py` | `gaussian-lsp` | 基础诊断包装 |
| **LintProvider** | `features/lint.py` | `lint` | G001-G040 规则 |
| **TypecheckProvider** | `features/typecheck.py` | `typecheck` | 关键词枚举/单位/必填段落 |
| **CodeActionProvider** | `features/code_actions.py` | — | 15+ 快速修复类型 |
| **FormattingProvider** | `features/formatting.py` | — | 非破坏性格式化 |
| **AgentAPIProvider** | `features/agent_api.py` | — | Agent JSON 快照 |

## LSP 功能注册

| LSP 方法 | 注册函数 | Provider |
|----------|----------|----------|
| `textDocument/completion` | completion() | 直接使用词汇表 |
| `textDocument/hover` | hover() | KEYWORD_DOCS |
| `textDocument/diagnostic` | diagnostic() | DiagnosticProvider + LintProvider |
| `textDocument/formatting` | formatting() | FormattingProvider |
| `textDocument/codeAction` | code_action() | CodeActionProvider |
| `textDocument/didOpen` | did_open() | 全部 Provider |
| `textDocument/didChange` | did_change() | 全部 Provider |

## 数据流

### 诊断管线
```
content: str
  → GJFParser.parse(content) → GaussianJob
  → _analyze_content(content) → List[LSP Diagnostic]
      ├── 结构诊断 (route/title/charge_mult 分隔符)
      ├── Link0 值诊断
      ├── Route 语义诊断
      ├── 化学诊断 (电子奇偶性)
      ├── 基组诊断 (Gen/GenECP)
      ├── 几何诊断 (坐标/ModRedundant)
      ├── Z-matrix 诊断
      └── TypecheckProvider.validate()
  → LintProvider.lint(content) → List[LSP Diagnostic]
  → 合并 → publish_diagnostics()
```

### Agent 序列化
```
LSP Diagnostic
  → diagnostic_to_dict()
  → agent_check_payload()
  → 确定性 JSON (含 code, severity, category, confidence, range, fix_hints)
```

## TypeScript 并行实现

Python 和 TypeScript 的双轨实现：

| 层面 | Python | TypeScript |
|------|--------|------------|
| 解析器 | `parser/gjf_parser.py` | `parsers/gjf.ts` |
| 诊断 | `features/lint.py` + server | `parsers/diagnostics.ts` |
| 测试 | pytest | Vitest |
| 类型检查 | mypy | tsc |

TypeScript 覆盖 6 条核心诊断规则（GAUSS-E030 到 GAUSS-E035），与 Python 规则互补。

## 格式化策略
FormattingProvider 对原始文本行操作（非 AST），确保非破坏性编辑。解析 → 重建 → 比较差异。

## 导航功能

| 功能 | 源文件 | 目标 |
|------|--------|------|
| Go to Definition | `features/definition.py` | Route 关键词、Z-matrix 变量 |
| Find References | `features/references.py` | Z-matrix 变量引用 |
| Rename | `features/rename.py` | 安全的 workspace edit |

## 测试基础设施

- **RegressionHarness**: Fixture 驱动的回归测试
- **TestRunnerProvider**: 可选的 Gaussian 可执行文件桥接
- **Golden fixtures**: 确定性快照比较

## 来源列表

- `src/gaussian_lsp/server.py` — 服务器核心、功能注册
- `src/gaussian_lsp/features/*.py` — 各 Provider 实现
- `src/parsers/*.ts` — TypeScript 并行实现
- `src/gaussian_lsp/rich_diagnostics.py` — 诊断序列化
- `src/gaussian_lsp/parser/gjf_parser.py` — GJFParser
- `src/gaussian_lsp/agent_lsp.py` — Agent LSP 封装
