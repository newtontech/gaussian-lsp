# Open Shell Systems

> 类型：概念
> 学科/领域：量子化学

## 定义

开壳层体系指含有未配对电子的分子或原子，其自旋多重度 > 1。这类体系需要特殊的量子化学方法处理。

## 核心机制

### 自旋多重度
多重度 = 2S + 1，其中 S 为总自旋量子数。

| 多重度 | 未配对电子数 | 示例 |
|--------|-------------|------|
| 1 (单重态) | 0 | 大多数闭壳层分子 |
| 2 (双重态) | 1 | 自由基 |
| 3 (三重态) | 2 | O₂ 基态 |

### 方法选择

| 方法 | 开壳层处理 | 适用场景 |
|------|-----------|----------|
| **RHF** | 不适用 | 仅闭壳层 |
| **UHF** | α/β 轨道独立 | 通用开壳层 |
| **ROHF** | 共享双占据 + 独立单占据 | 自旋污染敏感场景 |
| **DFT** | 隐式 unrestricted | 大多数开壳层 DFT |

### LSP 检测逻辑
- 多重度 > 1 时，检查是否使用了 RHF（不兼容）
- DFT 方法隐式使用 unrestricted 行为（不报警告）
- Post-HF 方法有自身的开壳层处理（不报警告）

### Guess=Mix 限制
`Guess=Mix` 用于打破 α/β 对称性，仅适用于 unrestricted/open-shell 计算。与 RHF 组合时报错。

### 电子数奇偶性
LSP 验证：总电子数 - 电荷的奇偶性必须与 (多重度 - 1) 的奇偶性一致。

## 应用场景

- 编写自由基或过渡金属络合物的输入文件时获得方法选择指导
- 自动检测电荷/多重度不匹配

## 相关概念

- [[HF_Methods]] — RHF/UHF/ROHF 方法详情
- [[DFT_Functionals]] — DFT 对开壳层的处理
- [[Gaussian_Input_Format]] — 电荷/多重度行格式
- [[Diagnostics_Rule_Catalog]] — G030: 开壳层方法选择规则

## 来源

- `src/gaussian_lsp/server.py` — _append_chemistry_diagnostics
- `src/gaussian_lsp/features/lint.py` — _check_open_shell
