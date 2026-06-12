# Gaussian Input File Format

> 类型：工具
> 创建日期：2026-06-12
> 来源数：3

## 简介

Gaussian 输入文件使用 `.gjf` 或 `.com` 扩展名，由多个段落组成。gaussian-lsp 完整支持所有标准段落，包括 ModRedundant、ONIOM 层标记和 Z-matrix 坐标。

## 文件结构

```text
%link0_commands         ← 可选，资源分配
%chk=water.chk
%mem=2GB
%nproc=4
                        ← 空行分隔
# route_section         ← 必需，以 # 开头
# B3LYP/6-31G(d) opt freq
                        ← 空行分隔
Title Line              ← 必需
                        ← 空行分隔
0 1                     ← 必需，电荷 自旋多重度
O  0.000000  0.000000  0.000000    ← 笛卡尔坐标
H  0.757160  0.586260  0.000000
H -0.757160  0.586260  0.000000
                        ← 空行分隔（结束几何段落）
[ModRedundant lines]    ← 可选
[Gen basis section]     ← 可选（使用 Gen/GenECP 时）
```

## 段落详解

### 1. Link0 段落（可选）
- 以 `%` 开头
- 格式：`%key=value`
- 详见 [[Link0_Commands]]

### 2. Route 段落（必需）
- 必须以 `#` 开头
- 包含：方法/基组 job_type 关键词选项
- 可跨多行（非空行自动续行）
- 详见 [[Route_Section_Syntax]]

### 3. Title 段落（必需）
- 一行自由文本描述

### 4. 分子规格（必需）
- 第一行：`charge multiplicity`（两个整数）
- 后续行：原子坐标
  - **笛卡尔**：`Element X Y Z`
  - **Z-matrix**：详见 [[Z_Matrix_Input]]
  - **ONIOM 层标记**：`Element(High/Low) X Y Z`

### 5. ModRedundant 段落（可选）
- 与 `Opt=ModRedundant` 配合
- 命令：`B`（键）、`A`（角）、`D`（二面角）、`L`（线性角）、`S`（扫描）、`F`（冻结）
- 格式：`Command atom1 atom2 [atom3 [atom4]] value`
- 详见 [[Gaussian_Input_Format]]

## 元素支持

- **完整周期表**：H 到 Og（118 种元素）
- **虚拟原子**：`X`（dummy）、`Bq`（Bq 电荷）
- 元素符号必须标准写法（首字母大写，如 `Fe` 而非 `FE`）

## 注释

- 以 `!` 开头的行视为注释，解析时跳过

## 安全限制

- 文件大小上限：10 MB
- 行数上限：100,000 行
- 单行长度上限：1,000 字符

## 官方语法规则（Gaussian 16 文档）

来源: gaussian.com/input/

1. 输入为 **自由格式**，**大小写不敏感**
2. 空格、制表符、逗号或斜杠均可作为分隔符；多个空格视为单个分隔符
3. 选项语法: `keyword=option`, `keyword(option)`, `keyword=(opt1,opt2,...)`
4. 所有关键词和选项可缩写为在 Gaussian 16 系统中的 **最短唯一前缀**
5. 外部文件包含: `@filename`（追加 `/N` 禁止回显）
6. 注释: `!` 可出现在行内任意位置

### Title 段落限制
- 不超过 **5 行**
- 避免使用: `@ # ! - _ \` 和控制字符

### Route 前缀
| 前缀 | 含义 |
|------|------|
| `#` / `#N` | 正常输出 |
| `#P` | 详细输出（推荐用于生产计算） |
| `#T` | 精简输出 |

### 多步 Job
使用 `--Link1--` 分隔多个 job step，每个 step 可重复 route/title/molecule 段落。

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — GJFParser、GaussianJob、VALID_ELEMENTS
- `src/gaussian_lsp/server.py` — _analyze_content
- `docs/docs.md` — 用户文档
- `raw/assets/gaussian-input-format.md` — gaussian.com/input/ 官方文档提取
- `raw/assets/gaussian-route-syntax.md` — Route section 详细语法参考
- `raw/assets/gaussian-examples.md` — 15 个完整输入文件示例

## 相关实体/概念

- [[Link0_Commands]] — Link0 命令详情
- [[Route_Section_Syntax]] — Route 段落语法
- [[Job_Types]] — 可用计算类型
- [[Z_Matrix_Input]] — Z-matrix 坐标格式
- [[Gen_Basis_Sections]] — 自定义基组段落

## 历史更新

- 2026-06-12: 初始创建
- 2026-06-12: 扩展官方语法规则、route 前缀、多步 job（来源: gaussian.com/input/）
