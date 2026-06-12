# Gaussian DSL Reference

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：3

## 核心论点

本文档是 Gaussian 输入 DSL 的完整语言参考，综合了 parser 词汇表、server 悬停文档和格式规范。它取代了分别查阅多个文件的需要。

## 文件格式总览

```text
[Link0 段落]          ← 可选，%key=value 格式
[空行]
# Route 段落          ← 必需，以 # 开头
[空行]
Title 行              ← 必需，自由文本
[空行]
charge multiplicity   ← 必需，两个整数
Atom X Y Z           ← 必需，原子坐标
...
[空行]
[ModRedundant 段落]   ← 可选
[Gen basis 段落]      ← 可选（使用 Gen/GenECP 时）
```

详见 [[Gaussian_Input_Format]]。

## Link0 命令

19 个命令，以 `%` 前缀，格式 `%key=value`。详见 [[Link0_Commands]]。

## Route 语法

```
# Method/BasisSet JobType Keyword=Value Keyword=(Opt1,Opt2)
```

详见 [[Route_Section_Syntax]]。

## 方法词汇 (66 entries)

| 类别 | 方法 |
|------|------|
| Hartree-Fock | HF, RHF, UHF, ROHF |
| Hybrid DFT | B3LYP, PBE0, B3PW91, B1B95, B1LYP, mPW1PW91, mPW1LYP, mPW3PBE, X3LYP, TPSSH |
| Range-Separated | wB97XD, wB97X, wB97, CAM-B3LYP, LC-wPBE, LC-wPBEh, WB97X-D3, MN12SX |
| GGA | PBE, BLYP, BP86, BP91, PW91, OPBE, OLYP, RPBE, revPBE |
| Meta-GGA | TPSS, revTPSS, M06, M06L, M06HF, BMK, VSXC |
| Double-Hybrid | B2PLYPD, mPW2PLYPD |
| Minnesota | M06, M062X, M06L, M06HF, MN12SX, MN12L, N12, N12SX |
| Post-HF | MP2, MP3, MP4, MP4SDQ, MP5, CCSD, CCSD(T), QCISD, QCISD(T), EOM-CCSD |
| 激发态 | CIS, CISD |
| Semi-empirical | PM3, PM6, PM7, AM1, RM1, MNDO, MNDOD, DFTB, DFTB3 |
| Other | HSEH1PBE, OHSE2PBE, HCTH, PW91PW91, XYG3, XYGJOS |

详见 [[HF_Methods]], [[DFT_Functionals]], [[Post_HF_Methods]]。

## 基组词汇 (82 entries)

| 族 | 数量 | 代表 |
|----|------|------|
| Pople | 28 | STO-3G, 6-31G(d), 6-311G(d,p) |
| Dunning | 12 | cc-pVDZ, cc-pVTZ, cc-pVQZ, aug-cc-pVTZ |
| Karlsruhe | 16 | def2-SVP, def2-TZVP, def2-QZVP |
| ECP | 8 | LANL2DZ, SDD, def2-ECP |
| Other | 18 | D95, EPR-II, PC-n, UGBS |

详见 [[Basis_Sets]]。

## Job Type 词汇 (31 entries)

| 类别 | 类型 |
|------|------|
| 能量 | SP, TD, CIS |
| 优化 | OPT, OPT FREQ, POPT, TS, Scan |
| 反应路径 | IRC, IRCMax |
| 频率/谱学 | FREQ, RAMAN, NMR, NMR=SpinSpin |
| 性质 | POLAR, FORCE, Density, Prop, Volume |
| 复合 | ONIOM, COUNTERPOISE, QM/MM, MM |
| 动力学 | ADMP, BOMD, MD |
| 分析 | Stable |

详见 [[Job_Types]]。

## 元素支持

118 种标准元素 (H-Og) + 2 种虚拟原子 (X, Bq)。

## 特殊语法

| 特性 | 说明 |
|------|------|
| **ModRedundant** | 几何段落后的坐标修改指令 |
| **ONIOM 层标记** | `Element(High)` / `Element(Low)` |
| **Z-matrix** | 内坐标格式 + 变量定义 |
| **Gen/GenECP** | 自定义基组段落，用 `****` 分隔 |
| **注释** | 以 `!` 开头的行 |

详见 [[Z_Matrix_Input]], [[Gen_Basis_Sections]]。

## 来源列表

- `src/gaussian_lsp/parser/gjf_parser.py` — 完整词汇表
- `src/gaussian_lsp/server.py` — 悬停文档和语义检查
- `docs/docs.md` — 用户文档
- `raw/assets/gaussian-input-format.md` — gaussian.com/input/ 官方输入格式
- `raw/assets/gaussian-route-syntax.md` — Route section 完整语法参考
- `raw/assets/gaussian-keywords-reference.md` — 完整关键词列表（方法/基组/job type/SCF/Link0）
- `raw/assets/gaussian-examples.md` — 15 个完整输入文件示例
- `raw/assets/gaussian-output-format.md` — 输出文件格式详解
- `raw/assets/gaussian-github-parsers.md` — 开源解析器参考

## 历史更新

- 2026-06-12: 初始创建
- 2026-06-12: 扩展外部来源列表，新增 5 个 raw/assets 文档
