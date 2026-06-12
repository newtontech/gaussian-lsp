# Gaussian Output Format

> 类型：概念
> 创建日期：2026-06-12
> 学科/领域：量子化学 / 输出解析

## 定义

Gaussian 16 输出文件是 ASCII 文本文件，按程序内部 "Links" 的执行顺序分段输出。每个 Link 产生特定类型的计算结果，可被自动化工具解析。

## 输出文件结构（按 Link 顺序）

### L0/L1: 头部与许可

```
Entering Gaussian System, Link 0=...
Copyright (c) 1988,...,2016, Gaussian, Inc.
Cite this work as: Gaussian 16, Revision A.03, M. J. Frisch, ...
```

### L1: Job 规格回显

```
******************************************
Gaussian 16: ES64L-G16RevA.03 25-Dec-2016
10-Mar-2020
******************************************
%chk=...
%mem=...
----------------------------------------------------------------------
#p b3lyp/6-31+G(d,p) opt ...
----------------------------------------------------------------------
```

**关键标记**: Route section 位于 `------` 行之间。

### L101: 标题与分子

```
----------------------------------------------------------------------
Title text
----------------------------------------------------------------------
Symbolic Z-matrix:
Charge = 0 Multiplicity = 1
...
NAtoms= 6
```

**关键标记**: `Charge = N Multiplicity = M`, `NAtoms= N`

### L103: 优化初始化

```
GradGradGradGradGradGradGradGradGradGradGradGradGradGradGradGradGradGrad
Berny optimization.
```

**关键标记**: `GradGradGrad...` 边界线, `Berny optimization`

### L202: 对称性与坐标

```
Stoichiometry  H4O2
Framework group  CS[SG(H2O2),X(H2)]
Standard orientation:
Center  Atomic  Atomic  Coordinates (Angstroms)
Number  Number  Type    X        Y        Z
```

### L301: 基组信息

```
Standard basis: 6-31+G(d,p) (6D, 7F)
58 basis functions, 92 primitive gaussians
nuclear repulsion energy  36.6574882778 Hartrees.
IExCor=  402 DFT=T Ex+Corr=B3LYP
```

**关键标记**: 基组名称, 基函数数量, 核排斥能

### L502: SCF 能量（核心段落）

```
SCF Done:  E(RB3LYP) =  -152.878894550  A.U. after  11 cycles
     NFock= 11  Conv=0.66D-08 -V/T= 2.0093
```

**正则模式**: `SCF Done:\s+E\((\w+)\)\s+=\s+(-?\d+\.\d+)\s+A\.U\.\s+after\s+(\d+)\s+cycles`

| 方法 | 输出标签 |
|------|---------|
| HF (restricted) | `E(RHF)` |
| HF (unrestricted) | `E(UHF)` |
| B3LYP (restricted) | `E(RB3LYP)` 或 `E(RB+HF-LYP)` |
| MP2 | `EUMP2` |
| CCSD | `E(CCSD)` |
| CCSD(T) | `E(CCSD(T))` |

### L601: 布居分析

```
Population analysis using the SCF density.
Alpha occ. eigenvalues -- -19.19882 ...
Alpha virt. eigenvalues --  0.00366 ...
Mulliken charges:
         1
  1  O   -0.763760
Dipole moment (Debye):
   X= -0.0631  Y= -3.0081  Z=  0.0000  Tot=  3.0088
```

### L716: 力和梯度

```
Center  Atomic       Forces (Hartrees/Bohr)
Number  Number    X             Y             Z
   1       8     0.000091919   0.000000000   0.000035477
Cartesian Forces:  Max  0.000107190 RMS  0.000048028
```

### L103: 优化步汇总

```
Item               Value     Threshold  Converged?
Maximum Force       0.000144   0.000045   NO
RMS     Force       0.000069   0.000030   NO
Maximum Displacement 0.000696  0.000180   NO
RMS     Displacement  0.000276  0.000120   NO
```

收敛后:
```
Optimization completed.
   -- Stationary point found.
```

### L9999: 归档条目

```
 1\1\GINC-R1\FOpt\RB3LYP\6-31+G(d,p)\H4O2\USER\10-Mar-2020\1\\
 #p b3lyp/6-31+G(d,p) opt...\\title\\0,1\O\H,1,r2\...\\
 r2=0.97321674\...\\Version=ES64L-G16RevA.03\State=1-A'\HF=-152.8788946\...
```

归档字段:
- `FOpt` = Full Optimization（job type）
- `RB3LYP` = 方法
- `6-31+G(d,p)` = 基组
- `HF=` = 最终能量（对所有方法适用，不仅仅是 HF）
- `State=` = 电子态
- `PG=` = 点群

### 终止

```
Normal termination of Gaussian 16 at ...
```
或
```
Error termination via Lnk1e in .../l502.exe at ...
```

## 关键正则模式

| 模式 | 正则 | 提取内容 |
|------|------|---------|
| SCF 能量 | `SCF Done:\s+E\((\w+)\)\s+=\s+(-?\d+\.\d+)` | 方法, 能量 |
| 正常终止 | `Normal termination` | Job 状态 |
| 错误终止 | `Error termination` | Job 状态 |
| 优化完成 | `Optimization completed.` | Opt 状态 |
| 频率 | `Frequencies --\s+(\d+\.\d+)` | 振动频率 |
| 电荷多重度 | `Charge = (\d+) Multiplicity = (\d+)` | 系统状态 |
| NAtoms | `NAtoms=(\d+)` | 系统大小 |
| 归档能量 | `HF=(-?\d+\.\d+)` | 最终能量 |

## 开源解析工具

| 工具 | 语言 | 输入解析 | 输出解析 |
|------|------|---------|---------|
| **cclib** | Python | 部分 | 完整 |
| **gaussianutility** | Python | 完整 | 完整 |
| **GaussParse** | Python | 否 | 完整 |
| **gaussian_wrangler** | Python | 完整 | 完整 |

## 相关概念

- [[Route_Section_Syntax]] — 输入语法（route section 在输出中回显）
- [[Gaussian_Input_Format]] — 输入文件格式
- [[SCF_Convergence]] — SCF 收敛策略
- [[Provider_Architecture]] — LSP Provider 如何使用输出解析结果

## 来源

- `raw/assets/gaussian-output-format.md` — 官方文档 + Zipse 教程提取
- `raw/assets/gaussian-github-parsers.md` — GitHub 解析器收集
- https://zipse.cup.uni-muenchen.de/teaching/computational-chemistry-2/topics/a-typical-gaussian-output-file/
