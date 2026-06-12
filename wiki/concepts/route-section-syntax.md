# Route Section Syntax

> 类型：概念
> 学科/领域：量子化学 / LSP 语法解析

## 定义

Route section 是 Gaussian 输入文件的核心段落，定义计算方法、基组和任务类型。必须以 `#` 开头，支持跨行续行和括号选项。

## 核心机制

### 基本格式
```
# Method/BasisSet JobType Keyword=Value
```

- `#` 前缀必需（`#`、`#p`、`#n` 控制打印级别）
- 方法与基组用 `/` 分隔
- Job type 是独立关键词
- 选项用 `Keyword=Value` 或 `Keyword=(Value1,Value2)` 格式

### Token 解析
Route section 被拆分为大写 tokens 进行匹配：
- 按 `空白`、`/`、`,`、`=`、`(`、`)` 分割
- `#` 前缀被去除
- 括号内容变为独立 tokens

### 多方法冲突检测
LSP 检测以下冲突：
- 多个 SCF 类型（RHF + UHF + ROHF 互斥）
- 多个方法（DFT + Post-HF + Semi-empirical 互斥）
- SP 与 OPT 互斥
- Semi-empirical 方法不应搭配显式基组

### 拼写检测
内置 typo 修正映射：

| 常见拼写错误 | 建议修正 |
|-------------|---------|
| `FREQENCY` | `freq` |
| `OPTIMIZE` | `opt` |
| `M06-2X` | `M062X` |
| `631G` | `6-31G` |
| `NPROCSHARED` | `%nprocshared`（应为 Link0 命令） |

### Lint 规则
- G001: 未知 route 关键词（warning）
- G002: Route 拼写错误（warning，提供修正建议）
- G020: 缺少 job type（warning，假设 SP）
- G021: FREQ 没有 OPT（warning）
- G022: OPT 收敛标准过松（warning）

## 应用场景

- 在编辑器中编写 Gaussian 输入时获得实时补全和语法检查
- AI agent 通过 [[Agent_API_Reference]] 查询合法 route tokens
- CI 管道中用 `gaussian-lsp-tool check` 验证输入合法性

## 相关概念

- [[HF_Methods]] / [[DFT_Functionals]] / [[Post_HF_Methods]] — 可用方法
- [[Basis_Sets]] — 可用基组
- [[Job_Types]] — 可用任务类型
- [[Diagnostics_Rule_Catalog]] — 完整规则目录

## 来源

- `src/gaussian_lsp/server.py` — _route_tokens, _append_route_semantic_diagnostics, ROUTE_TYPO_HINTS
- `src/gaussian_lsp/features/lint.py` — _TYPO_MAP, _ALL_VALID_TOKENS, lint rules
- `raw/assets/gaussian-route-syntax.md` — gaussian.com 官方 route section 语法参考
- `raw/assets/gaussian-keywords-reference.md` — 完整关键词列表（方法、基组、job type、选项）

## 历史更新

- 2026-06-12: 初始创建
- 2026-06-12: 扩展官方 route 语法参考（来源: gaussian.com/route/, gaussian.com/capabilities/）
