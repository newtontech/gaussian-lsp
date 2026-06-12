# Post-HF Methods

> 类型：方法
> 创建日期：2026-06-12
> 来源数：2

## 简介

Post-HF 方法在 Hartree-Fock 参考态基础上加入电子相关效应，是量子化学中最高精度的计算方法。gaussian-lsp 支持 12 种 Post-HF 方法。

## 关键属性

### Møller-Plesset 微扰理论
在 HF 基础上逐级添加相关能修正。

| 方法 | 阶数 | 精度 | 计算成本 |
|------|------|------|----------|
| **MP2** | 二阶 | 良好，约 80-90% 相关能 | O(N⁵) |
| **MP3** | 三阶 | 不一定比 MP2 好 | O(N⁶) |
| **MP4** | 四阶 | 较好 | O(N⁷) |
| **MP4SDQ** | 四阶 | 仅单双四重激发 | O(N⁷) |
| **MP5** | 五阶 | 理论上更精确 | O(N⁸) |

### Coupled Cluster（耦合簇）
量子化学的"金标准"方法族。

| 方法 | 激发阶 | 精度 | 典型用途 |
|------|--------|------|----------|
| **CCSD** | 单+双 | 高精度 | 小分子能量和性质 |
| **CCSD(T)** | 单+双+微扰三 | **金标准** | 基准计算、高精度能量 |
| **QCISD** | 单+双 | 类似 CCSD | QC 变体 |
| **QCISD(T)** | 单+双+微扰三 | 类似 CCSD(T) | QC 变体 |

### 激发态方法

| 方法 | 说明 |
|------|------|
| **CIS** | 单激发组态相互作用 — 最简单的激发态方法 |
| **CISD** | 单+双激发组态相互作用 |
| **EOM-CCSD** | 方程运动耦合簇 — 高精度激发态 |

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — GAUSSIAN_METHODS
- `src/gaussian_lsp/server.py` — POST_HF_METHODS 集合、KEYWORD_DOCS

## 相关实体/概念

- [[HF_Methods]] — Post-HF 的参考态
- [[DFT_Functionals]] — 更经济的电子相关方法
- [[SCF_Convergence]] — Post-HF 对 SCF 收敛有更高要求
- [[Diagnostics_Rule_Catalog]] — G031: Post-HF + loose SCF 警告

## 历史更新

- 2026-06-12: 初始创建
