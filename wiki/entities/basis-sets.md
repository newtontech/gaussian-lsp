# Basis Sets

> 类型：工具
> 创建日期：2026-06-12
> 来源数：2

## 简介

基组是量子化学计算中展开分子轨道的一组基函数。gaussian-lsp 识别 82 种基组，覆盖从最小基到四极 zeta 的全精度范围。

## 按族分类

### Pople 基组（最常用）
由 John Pople 设计的经典基组族。

| 基组 | Zeta | 扩散 | 极化 | 典型用途 |
|------|------|------|------|----------|
| **STO-3G** | 最小 | — | — | 快速定性分析 |
| **3-21G** | 双 | 可选 | 可选 | 初步优化 |
| **6-31G** | 双 | 可选 | 可选 | 标准计算 |
| **6-31G(d)** | 双 | — | 重原子 | 几何优化 |
| **6-31G(d,p)** | 双 | — | 全原子 | 较精确几何 |
| **6-311G** | 三 | 可选 | 可选 | 能量计算 |
| **6-311G(d,p)** | 三 | — | 全原子 | 高精度能量 |
| **6-311++G(3df,3pd)** | 三 | ✓ | 高级 | 接近基组极限 |

### Dunning 相关一致基组
专为相关方法（Post-HF）设计，可系统收敛。

| 基组 | Zeta | 说明 |
|------|------|------|
| **cc-pVDZ** | 双 | 基础相关计算 |
| **cc-pVTZ** | 三 | 常用高精度计算 |
| **cc-pVQZ** | 四 | 接近 CBS 极限 |
| **cc-pV5Z** | 五 | CBS 外推用 |
| **aug-cc-pVDZ** 等 | — | 加扩散函数，适合阴离子和 Rydberg 态 |
| **cc-pCVXZ** | — | 核相关基组 |

### Karlsruhe def2 基组
Ahlrichs 设计，覆盖元素范围广。

| 基组 | Zeta | 说明 |
|------|------|------|
| **def2-SVP** | 双+极化 | 快速计算 |
| **def2-TZVP** | 三+极化 | 精度/速度平衡 |
| **def2-QZVP** | 四+极化 | 高精度 |
| **def2-TZVPP** 等 | — | 加额外极化 |
| **ma-def2-*** | — | 最小扩散增强版 |
| **def2-*/J** | — | RI-J 密度拟合辅助基组 |

### 赝势基组 (ECP)
用有效核势替代内层电子，适用于重元素。

| 基组 | 适用范围 |
|------|----------|
| **LANL2DZ** | 第一行过渡金属及更重元素 |
| **LANL2MB** | 最小基 + ECP |
| **SDD** | Stuttgart-Dresden ECP |
| **def2-ECP** | def2 系列的 ECP 版本 |
| **cc-pVXZ-PP** | Dunning 系列的 PP 版本 |

### 其他基组

| 基组 | 说明 |
|------|------|
| **D95/D95V** | Dunning-Huzinaga 基组 |
| **EPR-II/EPR-III** | EPR 超精细耦合专用 |
| **PC-1 到 PC-4** | Jensen 极化一致基组 |
| **UGBS** | 万有 Gaussian 基组 |

## 官方参考（Gaussian 16 文档）

来源: gaussian.com/basissets/

### 极化和扩散函数后缀规则

| 后缀 | 含义 |
|------|------|
| `(d)` | 重原子 1 组 d 极化 |
| `(d,p)` | 重原子 d + H 原子 p |
| `(2df,2pd)` | 重原子 2d1f + H 2p1d |
| `(3df,3pd)` | 重原子 3d1f + H 3p1d |
| `*` | 等同于 `(d)` |
| `**` | 等同于 `(d,p)` |
| `+` | 重原子添加扩散函数 |
| `++` | 所有原子添加扩散函数 |

### Dunning AUG- 前缀

`AUG-` 前缀为每种已有角动量类型添加一个扩散函数。

Truhlar "日历" 变体:
- `Jul-cc-pVDZ` — 移除 H/He 扩散
- `Jun-cc-pVDZ` — 进一步移除最高角动量扩散
- `May-cc-pVDZ` — 移除两个最高角动量扩散

### 各基组适用范围（官方表）

| 基组 | 适用元素 | 极化 | 扩散 |
|------|---------|------|------|
| 3-21G | H-Xe | 无实际极化 | — |
| 6-31G | H-Kr | 至 (3df,3pd) | +, ++ |
| 6-311G | H-Kr | 至 (3df,3pd) | +, ++ |
| D95 | H-Cl | 至 (3df,3pd) | +, ++ |
| cc-pVDZ | H-Ar, Ca-Kr | 内含 | AUG- 前缀 |
| cc-pVTZ | H-Ar, Ca-Kr | 内含 | AUG- 前缀 |
| Def2 系列 | H-La, Hf-Rn | 内含 | — |
| SDD | 除 Fr, Ra | — | — |

### 特殊基组

| 基组 | 说明 |
|------|------|
| `CBSB7` | CBS-QB3 使用 (6-311G(2d,d,p)) |
| `MTSmall` | Martin-de Oliveira W1 方法 |
| `MidiX` | Truhlar MIDI! 基组 |
| `EPR-II/EPR-III` | Barone EPR 超精细耦合专用 |
| `UGBS` | 万有 Gaussian 基组，可加 UGBS1P/2P/3P 极化 |

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — GAUSSIAN_BASIS_SETS 列表
- `src/gaussian_lsp/server.py` — KEYWORD_DOCS、ECP_BASIS_MARKERS
- `raw/assets/gaussian-keywords-reference.md` — gaussian.com/basissets/ 完整参考

## 相关实体/概念

- [[DFT_Functionals]] — 泛函精度依赖基组质量
- [[HF_Methods]] / [[Post_HF_Methods]] — 不同方法对基组的需求不同
- [[Gen_Basis_Sections]] — 自定义基组输入语法
- [[Route_Section_Syntax]] — 如何在 route 中指定基组

## 历史更新

- 2026-06-12: 初始创建
- 2026-06-12: 扩展官方极化/扩散后缀、适用范围、特殊基组（来源: gaussian.com/basissets/）
