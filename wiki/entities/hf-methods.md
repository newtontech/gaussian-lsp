# Hartree-Fock Methods

> 类型：方法
> 创建日期：2026-06-12
> 来源数：2

## 简介

Hartree-Fock (HF) 是最基础的 ab initio 量子化学方法，使用单个 Slater 行列式近似多电子波函数。gaussian-lsp 支持 4 种 HF 变体。

## 关键属性

| 方法 | 说明 | 适用体系 |
|------|------|----------|
| **HF** | 通用 Hartree-Fock | 闭壳层默认 |
| **RHF** | Restricted HF | 闭壳层（所有电子配对） |
| **UHF** | Unrestricted HF | 开壳层（α/β 自旋不同轨道） |
| **ROHF** | Restricted Open-shell HF | 开壳层（共享双占据轨道） |

- **精度**：不含电子相关能，通常高估能量
- **计算成本**：O(N³) — N 为基函数数量
- **典型用途**：定性分析、几何优化的初始方法、Post-HF 计算的参考态

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — GAUSSIAN_METHODS 列表
- `src/gaussian_lsp/server.py` — KEYWORD_DOCS 悬停文档

## 相关实体/概念

- [[DFT_Functionals]] — 包含电子相关的密度泛函方法
- [[Post_HF_Methods]] — 以 HF 为参考态的高精度方法
- [[Open_Shell_Systems]] — RHF/UHF/ROHF 选择策略
- [[SCF_Convergence]] — HF 的自洽场收敛行为

## 历史更新

- 2026-06-12: 初始创建
