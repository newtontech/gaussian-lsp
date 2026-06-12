# LLM Wiki Log

## 2026-06-12 — Wiki 初始化

**操作**: Initialize LLM Wiki from project knowledge
**来源覆盖**: 6 个核心源文件（parser, server, lint, rich_diagnostics, docs/*, diagnostics/*）
**创建页面**: 19 个 wiki 页面 + 7 个 raw 来源

### Entities (8)
- HF_Methods, DFT_Functionals, Post_HF_Methods, Basis_Sets, Job_Types, Link0_Commands, Gaussian_Input_Format, OpenQC_VSCode

### Concepts (6)
- Route_Section_Syntax, Diagnostic_Engine_V1, Open_Shell_Systems, Z_Matrix_Input, Gen_Basis_Sections, SCF_Convergence

### Synthesis (5)
- Diagnostics_Rule_Catalog, Agent_API_Reference, DSL_Reference, Provider_Architecture, Development_Workflow

### Raw Sources (7)
- diagnostic-engine-v1.md, agent-verification-loop.md, openqc-alignment.md, docs-overview.md, parser-vocabulary.md, diagnostic-schema.md, keyword-docs.md

**关键发现**: gaussian-lsp 包含三层诊断规则（Python lint G0xx-G3xx 共 11 条、TypeScript GAUSS-Exxx/Wxxx 共 8 条、Server 内置 30+ 条），覆盖 66 种方法、82 种基组、31 种 job type，提供完整的 Agent JSON API。

## 2026-06-12 — 文档扩展：Gaussian 官方文档收集

**操作**: Expand Gaussian documentation collection from web sources
**来源覆盖**: 6 个新 raw asset 文件（来自 gaussian.com、Zipse 教程、GitHub）
**创建/更新页面**: 1 新建 wiki 页面 + 5 更新页面 + 6 新 raw 来源

### 新 Raw Assets (6)
- gaussian-input-format.md — gaussian.com/input/ 官方输入格式
- gaussian-route-syntax.md — Route section 语法（方法/基组/job type/选项）
- gaussian-keywords-reference.md — 完整关键词参考（DFT 50+ 泛函、基组、SCF 选项、Link0、Links）
- gaussian-examples.md — 15 个完整输入文件示例（HF/DFT/MP2/TD-DFT/NMR/ONIOM/IRC/CBS-QB3）
- gaussian-output-format.md — 输出文件格式详解（15 个 Link 段落、正则模式、解析工具）
- gaussian-github-parsers.md — 开源解析器参考（cclib, gaussianutility, GaussParse 等）

### 新 Concept Pages (1)
- Gaussian_Output_Format — 输出文件格式、Link 执行顺序、关键正则模式

### 更新页面 (5)
- Gaussian_Input_Format — 新增官方语法规则、route 前缀、多步 job
- Link0_Commands — 新增官方命令完整表（含 %OldChk, %SChk, %GPUCPU 等）
- DFT_Functionals — 新增色散修正、交换/相关组合、自定义 IOp 参数
- Basis_Sets — 新增官方极化/扩散后缀规则、适用范围表、特殊基组
- DSL_Reference — 新增外部来源列表

### 更新索引/日志
- index.md — 新增 6 个 raw source 条目 + 1 个 concept page 条目
- log.md — 本条目

**关键发现**: Gaussian 16 官方文档涵盖 120+ 个关键词、50+ DFT 泛函、25+ 基组族、19 种 Link0 命令、完整 SCF 选项集。输出文件按 15+ 个 Link 段落分段，可通过正则提取能量/梯度/频率/归档条目。开源解析器以 cclib 最为完整（2000+ 行解析逻辑）。
