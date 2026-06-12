# Gaussian LSP Wiki

> Karpathy-style LLM Wiki for [newtontech/gaussian-lsp](https://github.com/newtontech/gaussian-lsp)
> 初始化日期：2026-06-12

本 wiki 将 gaussian-lsp 项目中散布在代码、文档和测试中的领域知识结构化为可浏览的知识库。

## 快速入口

| 角色 | 推荐页面 |
|------|----------|
| **计算化学家** | [[DSL_Reference]] — Gaussian 输入语言完整参考 |
| **开发者** | [[Provider_Architecture]] — LSP Provider 架构和数据流 |
| **AI Agent** | [[Agent_API_Reference]] — Agent-facing JSON API |

## Entity Pages

### 计算方法

- [[HF_Methods]] — Hartree-Fock 方法（HF, RHF, UHF, ROHF）
- [[DFT_Functionals]] — 密度泛函（40+ 泛函，按 Hybrid/GGA/Meta-GGA/Range-Separated 分类）
- [[Post_HF_Methods]] — Post-HF 方法（MP2, CCSD, CCSD(T) 等）
- [[Job_Types]] — 计算任务类型（SP, OPT, FREQ, TS, IRC 等 31 种）

### 基组与输入

- [[Basis_Sets]] — 基组（82 种，按 Pople/Dunning/Karlsruhe/ECP 分类）
- [[Link0_Commands]] — Link0 命令（19 种，资源分配和文件管理）
- [[Gaussian_Input_Format]] — .gjf/.com 文件格式完整定义

### 工具与框架

- [[OpenQC_VSCode]] — OpenQC VS Code 扩展对齐要求

## Concept Pages

### 语法与解析

- [[Route_Section_Syntax]] — Route 段落语法、token 解析、拼写检测
- [[Z_Matrix_Input]] — Z-matrix 内坐标格式和变量导航
- [[Gen_Basis_Sections]] — Gen/GenECP 自定义基组段落

### 诊断与验证

- [[Diagnostic_Engine_V1]] — Diagnostic Engine v1 诊断标准（严重性、类别、JSON 形状）
- [[SCF_Convergence]] — SCF 收敛策略和 Post-HF 要求
- [[Open_Shell_Systems]] — 开壳层体系的方法选择和奇偶性校验
- [[Gaussian_Output_Format]] — 输出文件格式、Link 顺序、关键正则模式

## Synthesis Pages

- [[Diagnostics_Rule_Catalog]] — 所有诊断规则的完整目录（Python lint + TypeScript + Server 内置）
- [[Agent_API_Reference]] — Agent-facing JSON API 完整参考（CLI、Python、LSP）
- [[DSL_Reference]] — Gaussian 输入 DSL 完整语言参考
- [[Provider_Architecture]] — Provider 层次架构、数据流和 TypeScript 并行
- [[Development_Workflow]] — 开发环境、测试、质量门禁和 PR 审查流程

## Raw Sources

| 文件 | 来源 |
|------|------|
| `raw/assets/diagnostic-engine-v1.md` | `docs/DIAGNOSTIC_ENGINE_V1.md` |
| `raw/assets/agent-verification-loop.md` | `docs/agent-verification-loop.md` |
| `raw/assets/openqc-alignment.md` | `docs/OPENQC_ALIGNMENT.md` |
| `raw/assets/docs-overview.md` | `docs/docs.md` |
| `raw/assets/parser-vocabulary.md` | `src/gaussian_lsp/parser/gjf_parser.py` — 词汇表提取 |
| `raw/assets/diagnostic-schema.md` | `diagnostics/diagnostic-engine-v1.schema.json` — Schema 摘要 |
| `raw/assets/keyword-docs.md` | `src/gaussian_lsp/server.py` — KEYWORD_DOCS 提取 |
| `raw/assets/gaussian-input-format.md` | gaussian.com/input/ — 官方输入格式文档 |
| `raw/assets/gaussian-route-syntax.md` | gaussian.com/route/ + capabilities/ — Route section 语法参考 |
| `raw/assets/gaussian-keywords-reference.md` | gaussian.com/keywords/ + basissets/ + scf/ + link0/ — 完整关键词参考 |
| `raw/assets/gaussian-examples.md` | gaussian.com/input/ + GitHub — 15 个完整输入文件示例 |
| `raw/assets/gaussian-output-format.md` | Zipse 教程 + cclib — 输出文件格式详解 |
| `raw/assets/gaussian-github-parsers.md` | GitHub (cclib, gaussianutility, GaussParse) — 开源解析器 |
