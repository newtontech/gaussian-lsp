# Diagnostics Rule Catalog

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：5

## 核心论点

gaussian-lsp 实现了三层诊断规则：Python lint 规则（G0xx-G3xx）、TypeScript 规则（GAUSS-Exxx/Wxxx）、以及 server 内置的结构/语义/化学诊断。本文档是所有诊断规则的完整参考目录。

## Python Lint 规则

由 `LintProvider` (`src/gaussian_lsp/features/lint.py`) 生成。

| 规则码 | 名称 | 严重性 | 类别 | 触发条件 |
|--------|------|--------|------|----------|
| **G001** | unknown_route_keyword | warning | schema | Route 中出现未知关键词 |
| **G002** | route_typo | warning | schema | Route 关键词疑似拼写错误（提供修正） |
| **G010** | unknown_link0 | warning | schema | 未知 Link0 命令 |
| **G011** | unusual_nproc | warning | type/value | %nproc 值异常（如 1） |
| **G012** | low_mem | warning | type/value | %mem 值过低 (< 128 MB) |
| **G020** | no_job_type | warning | schema | Route 中缺少 job type |
| **G021** | freq_without_opt | warning | semantic consistency | FREQ 未与 OPT 配合 |
| **G022** | opt_loose_convergence | warning | semantic consistency | OPT 收敛标准过松 |
| **G030** | open_shell_no_unrestricted | warning | semantic consistency | 开壳层体系未用 unrestricted 方法 |
| **G031** | post_hf_loose_scf | warning | semantic consistency | Post-HF 方法搭配 loose SCF |
| **G040** | verbosity_hint | hint | style/deprecation | 建议使用最低打印级别 |

## TypeScript 规则

由 `diagnostics.ts` (`src/parsers/diagnostics.ts`) 生成。

| 规则码 | 严重性 | 触发条件 |
|--------|--------|----------|
| **GAUSS-E030** | error | 缺少 route section |
| **GAUSS-E031** | error | 无效的电荷/多重度 |
| **GAUSS-W030** | warning | 未知 route 关键词 |
| **GAUSS-W031** | warning | 方法/基组不兼容 |
| **GAUSS-E032** | error | 无效的 %mem 值 |
| **GAUSS-E033** | error | 无效的 %nproc 值 |
| **GAUSS-E034** | error | SCF 未收敛 |
| **GAUSS-E035** | error | 几何解析失败 |

## Server 内置诊断

由 `_analyze_content()` (`src/gaussian_lsp/server.py`) 生成，无需单独的 lint 规则码。

| 来源函数 | 严重性 | 触发条件 |
|----------|--------|----------|
| 结构诊断 | error | 缺少空行分隔符 |
| 结构诊断 | error | 无效的电荷/多重度格式 |
| 结构诊断 | error | 缺少电荷/多重度行 |
| Link0 诊断 | error | %chk/%oldchk 值为空 |
| Link0 诊断 | error | %mem 值格式错误 |
| Link0 诊断 | error | %nproc 值非正整数 |
| Route 语义 | error | 括号不匹配 |
| Route 语义 | error | 常见拼写错误 (typo hints) |
| Route 语义 | error | 互斥 SCF 方法 |
| Route 语义 | error | 冲突的计算方法 |
| Route 语义 | error | SP + OPT 互斥 |
| Route 语义 | error | 多个基组 |
| Route 语义 | error | 半经验方法 + 显式基组 |
| Route 语义 | error | Guess=Mix + RHF |
| Route 语义 | error | Opt=ModRedundant 无段落 |
| 化学诊断 | error | 电子数奇偶性不匹配 |
| 基组诊断 | error | Gen 缺少 **** 分隔符 |
| 基组诊断 | error | GenECP 缺少 ECP 块 |
| 基组诊断 | error | 基组中心行格式错误 |
| 基组诊断 | error | 元素不在几何中 |
| 基组诊断 | warning | ECP 基组用于轻元素 |
| 几何诊断 | error | 无效坐标行 |
| 几何诊断 | error | ModRedundant 命令参数错误 |
| 几何诊断 | error | ModRedundant 原子索引越界 |
| 几何诊断 | warning | 原子间距过近 (< 0.1 Å) |
| Z-matrix | error | 混合笛卡尔/Z-matrix 行 |
| Z-matrix | error | Z-matrix 参考位置非整数 |
| Z-matrix | error | 无效变量定义格式 |
| Z-matrix | error | 未定义变量 |
| 核心 | error | 缺少 route section |
| 核心 | error | Route 不以 # 开头 |
| 核心 | error | 几何段落无原子 |
| 核心 | warning | 未知元素 |
| 核心 | error | 无效多重度 |
| 核心 | warning | 无可识别方法 |
| 核心 | warning | 无可识别基组 |

## 证据梳理

每条规则都有对应的测试 fixture 在 `tests/fixtures/rules/` 中，确保确定性回归。

## 操作框架

### 通过 CLI 检查
```bash
gaussian-lsp-tool check input.gjf --format json
```

### 通过 Agent API
```python
from gaussian_lsp.agent_lsp import AgentLSP

agent = AgentLSP.from_path("input.gjf")
result = agent.check()
for d in result["diagnostics"]:
    print(f"{d['code']}: {d['message']}")
```

## 开放问题

- 运行时 log 解析规则仍在扩展中（新的 GAUSS-Exxx 规则会随新日志模式添加）
- 某些诊断的 confidence 值需要更精细的分级

## 来源列表

- `src/gaussian_lsp/features/lint.py` — Python lint 规则定义
- `src/gaussian_lsp/server.py` — 内置结构/语义/化学诊断
- `src/parsers/diagnostics.ts` — TypeScript 规则
- `src/gaussian_lsp/rich_diagnostics.py` — 诊断序列化
- `tests/fixtures/rules/` — 规则测试 fixtures
