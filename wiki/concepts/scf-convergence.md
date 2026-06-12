# SCF Convergence

> 类型：概念
> 学科/领域：量子化学

## 定义

自洽场 (SCF) 收敛是 HF 和 DFT 计算的核心迭代过程。收敛失败是 Gaussian 运行时最常见的错误之一。

## 核心机制

### SCF 算法选项

| 选项 | 算法 | 适用场景 |
|------|------|----------|
| **DIIS** | 直接反转迭代子空间 | 默认，大多数体系 |
| **QC** | 二次收敛 | 难收敛体系 |
| **XQC** | 先 DIIS 后 QC | 安全选择 |
| **YQC** | 先 DIIS 后变尺度 | 中等难度 |

### 收敛级别

| 级别 | 说明 | 典型用途 |
|------|------|----------|
| **Loose** | 宽松收敛 | 几何优化初期 |
| **Tight** | 紧收敛 | 精确能量计算 |
| **VeryTight** | 极紧收敛 | 高精度要求 |

### Post-HF 要求
Post-HF 方法（MP2, CCSD 等）需要更紧的 SCF 收敛。使用 `SCF=Tight` 或更好。

### LSP 检测

**G031 规则**：当 Post-HF 方法搭配 `SCF=Loose` 时发出警告。

### 运行时错误
TypeScript parser 检测 Gaussian log 文件中的 SCF 收敛失败：
- 规则码：`GAUSS-E034`
- 匹配 "Convergence failure" 或类似日志输出

## 应用场景

- 在编辑输入时获得 SCF 收敛建议
- Agent 自动选择合适的 SCF 策略

## 相关概念

- [[HF_Methods]] — SCF 是 HF 的核心迭代
- [[Post_HF_Methods]] — Post-HF 对 SCF 收敛有更高要求
- [[Diagnostics_Rule_Catalog]] — G031: Post-HF + loose SCF

## 来源

- `src/gaussian_lsp/features/lint.py` — _check_scf_convergence
- `src/gaussian_lsp/features/typecheck.py` — _ENUM_KEYWORDS["SCF"]
- `src/parsers/diagnostics.ts` — SCF 收敛失败日志解析
