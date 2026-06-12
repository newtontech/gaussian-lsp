# Job Types

> 类型：方法
> 创建日期：2026-06-12
> 来源数：2

## 简介

Job type 定义 Gaussian 要执行的计算类型。gaussian-lsp 识别 31 种 job type，从单点能量到分子动力学。

## 关键属性

### 能量计算

| Job Type | 说明 | 典型组合 |
|----------|------|----------|
| **SP** | 单点能量计算（默认） | 任何方法/基组 |
| **TD** | 含时 DFT，激发态 | 需 DFT 方法 |
| **CIS** | 组态相互作用单激发 | HF 或 DFT |

### 几何优化

| Job Type | 说明 | 注意事项 |
|----------|------|----------|
| **OPT** | 几何优化（找极小值） | 优化后建议做 FREQ |
| **OPT FREQ** | 优化 + 频率分析 | 确认是极小值（无虚频） |
| **POPT** | 部分优化 | 冻结部分坐标 |
| **Scan** | 势能面扫描 | 反应路径探索 |

### 过渡态与反应路径

| Job Type | 说明 | 注意事项 |
|----------|------|----------|
| **TS** | 过渡态优化 | 需好的初始猜测 |
| **IRC** | 内禀反应坐标 | 从 TS 出发跟踪反应路径 |
| **IRCMax** | IRC 上能量最大点 | 与 IRC 配合使用 |

### 频率与谱学

| Job Type | 说明 |
|----------|------|
| **FREQ** | 频率分析（振动频率） |
| **RAMAN** | Raman 活性计算 |
| **NMR** | NMR 化学位移 |
| **NMR=SpinSpin** | 自旋-自旋耦合常数 |

### 性质计算

| Job Type | 说明 |
|----------|------|
| **POLAR** | 极化率和超极化率 |
| **Polar=Numer** | 数值极化率 |
| **FORCE** | 力的计算 |
| **Density** | 电子密度分析 |
| **Prop** | 性质计算 |
| **Volume** | 分子体积 |

### 复合方法

| Job Type | 说明 |
|----------|------|
| **ONIOM** | 多层组合方法（高/低精度层） |
| **COUNTERPOISE** | 基组叠加误差校正 |
| **QM/MM** | 量子/分子力学组合 |
| **MM** | 纯分子力学 |

### 分子动力学

| Job Type | 说明 |
|----------|------|
| **ADMP** | 含时 DFT 分子动力学 |
| **BOMD** | Born-Oppenheimer 分子动力学 |
| **MD** | 经典分子动力学 |

### 稳定性分析

| Job Type | 说明 |
|----------|------|
| **Stable** | 波函数稳定性分析 |

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — GAUSSIAN_JOB_TYPES 列表
- `src/gaussian_lsp/server.py` — KEYWORD_DOCS 悬停文档

## 相关实体/概念

- [[Route_Section_Syntax]] — Job type 在 route 中的语法
- [[Gaussian_Input_Format]] — 完整输入文件结构
- [[Diagnostics_Rule_Catalog]] — G020: 缺少 job type 警告、G021: FREQ 无 OPT

## 历史更新

- 2026-06-12: 初始创建
