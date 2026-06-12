# DFT Functionals

> 类型：方法
> 创建日期：2026-06-12
> 来源数：2

## 简介

密度泛函理论 (DFT) 泛函是量子化学中最常用的计算方法。gaussian-lsp 识别 40+ 种 DFT 泛函，涵盖 GGA、meta-GGA、hybrid、range-separated、double-hybrid 和半经验 DFT 等类型。

## 分类

### Hybrid（杂化泛函）
含部分精确交换，兼顾精度和效率。

| 泛函 | 精确交换 | 特点 |
|------|----------|------|
| **B3LYP** | 20% | 最流行的泛函，通用性好 |
| **PBE0** | 25% | PBE 杂化版本，热化学精度好 |
| **B3P86** | 20% | B3LYP 的 Perdew 86 变体 |
| **B3PW91** | 20% | B3LYP 的 PW91 变体 |
| **B1B95** | — | 单参数杂化 |
| **B1LYP** | — | B1B95 的 LYP 变体 |
| **mPW1PW91** | — | 修改的 PW91 杂化 |
| **mPW1LYP** | — | mPW + LYP 杂化 |
| **mPW3PBE** | — | 三参数杂化 |
| **X3LYP** | — | 扩展的 B3LYP |
| **TPSSH** | — | TPSS 杂化版本 |

### Range-Separated（长程修正）
短程和长程使用不同泛函，改善电荷转移和 Rydberg 态。

| 泛函 | 特点 |
|------|------|
| **wB97XD** | 含色散修正的长程修正杂化泛函 |
| **wB97X** | 长程修正杂化泛函 |
| **wB97** | 长程修正泛函 |
| **CAM-B3LYP** | Coulomb 衰减 B3LYP，适合电荷转移 |
| **LC-wPBE** | 长程修正 PBE |
| **LC-wPBEh** | 长程修正 PBEh |
| **WB97X-D3** | wB97X + D3 色散 |
| **MN12SX** | Minnesota 范围分离泛函 |

### GGA（广义梯度近似）
仅依赖电子密度及其梯度。

| 泛函 | 特点 |
|------|------|
| **PBE** | 无经验参数，通用 GGA |
| **BLYP** | Becke 交换 + LYP 相关 |
| **BP86** | Becke 交换 + Perdew 86 相关 |
| **BP91** | Becke 交换 + PW91 相关 |
| **PW91** | Perdew-Wang 1991 |
| **PW91PW91** | PW91 交换 + PW91 相关 |
| **OPBE** | OPTX 交换 + PBE 相关 |
| **OLYP** | OPTX 交换 + LYP 相关 |
| **RPBE** | PBE 的修正版本 |

### Meta-GGA
额外依赖动能密度。

| 泛函 | 特点 |
|------|------|
| **TPSS** | 无经验参数的 meta-GGA |
| **revTPSS** | TPSS 修订版 |
| **M06** | Minnesota 2006，适合过渡金属 |
| **M06L** | M06 的纯泛函版本 |
| **M06HF** | M06 + 100% 精确交换 |
| **VSXC** | meta-GGA 泛函 |

### Double-Hybrid
混合 DFT + MP2 微扰。

| 泛函 | 特点 |
|------|------|
| **B2PLYPD** | 双杂化 + 色散 |
| **mPW2PLYPD** | mPW 双杂化 + 色散 |

## 色散修正

| 关键词 | 说明 |
|--------|------|
| `EmpiricalDispersion=GD2` | Grimme D2 |
| `EmpiricalDispersion=GD3` | Grimme D3 原始阻尼 |
| `EmpiricalDispersion=GD3BJ` | Grimme D3 Becke-Johnson 阻尼 |
| `EmpiricalDispersion=PFD` | Petersson-Frisch 色散 |

含内置色散的泛函: APFD, B97D, B97D3, wB97XD, B2PLYPD, B2PLYPD3, mPW2PLYPD。

## 交换/相关泛函组合

DFT 泛函可通过组合交换和相关成分构建:
- **交换泛函**: S, XA, B, PW91, mPW, G96, PBE, O, TPSS, RevTPSS
- **相关泛函**: VWN, VWN5, LYP, PL, P86, PW91, B95, PBE, TPSS

组合示例: `BLYP` = B(交换) + LYP(相关), `SVWN`/`LSDA` = S(交换) + VWN(相关)

前缀 `LC-` 可添加到任何纯泛函以应用长程修正: `LC-BLYP`。

## 自定义泛函参数

通过 IOp 控制杂化比例:
```
IOp(3/76=mmmmmnnnnn)  — P1 = mmmmm/10000, P2 = nnnnn/10000
IOp(3/77=mmmmmnnnnn)  — P3, P4
IOp(3/78=mmmmmnnnnn)  — P5, P6
```

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — GAUSSIAN_METHODS 中的 DFT 条目
- `src/gaussian_lsp/server.py` — DFT_METHODS 集合、KEYWORD_DOCS
- `raw/assets/gaussian-keywords-reference.md` — 官方 DFT 泛函完整参考（来源: gaussian.com + wild.life.nctu.edu.tw）

## 相关实体/概念

- [[HF_Methods]] — DFT 的基础参考方法
- [[Post_HF_Methods]] — 更高精度但更昂贵的方法
- [[Basis_Sets]] — 泛函精度依赖基组质量
- [[SCF_Convergence]] — DFT 的 SCF 收敛策略
- [[Route_Section_Syntax]] — 如何在 route 中指定泛函

## 历史更新

- 2026-06-12: 初始创建
- 2026-06-12: 扩展色散修正、交换/相关组合、自定义参数（来源: gaussian.com DFT 文档）
