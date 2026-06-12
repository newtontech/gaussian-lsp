# Gen/GenECP Basis Sections

> 类型：概念
> 学科/领域：量子化学 / 输入格式

## 定义

Gen 和 GenECP 关键词允许在输入文件中自定义基组和有效核势 (ECP)，而非使用内置基组名称。

## 核心机制

### Gen 基组段落
Route 中使用 `Gen` 替代基组名称后，在几何段落之后添加自定义基组块：

```text
C  0
6-31G(d)
****
H  0
6-31G(d,p)
****
```

- `****` 分隔不同元素的基组定义
- 每个块第一行：`Element  0`（必须以 0 结尾）
- 后续行：基组定义（从 Gaussian 基组库格式）

### GenECP 基组段落
GenECP 在基组块之后还需要 ECP 块：

```text
Au  0
SDD
****
Pt  0
SDD
****

Au  0
SDD
****
Pt  0
SDD
****
```

- 前半部分为基组，后半部分为 ECP
- 至少需要两组 `****` 分隔符

### LSP 验证

| 检查 | 条件 | 严重性 |
|------|------|--------|
| 缺少 `****` | Gen 被指定但无分隔符 | error |
| 缺少 ECP 块 | GenECP 被指定但分隔符不足 | error |
| 基组中心行格式错误 | 行尾不是 `0` | error |
| 元素不在几何中 | 自定义基组引用了不存在的元素 | error |
| ECP 用于轻元素 | ECP 基组 + 无重元素 (Z>36) | warning |

## 应用场景

- 混合基组计算（不同元素用不同精度基组）
- 使用文献中的自定义基组
- 重元素需要 ECP

## 相关概念

- [[Basis_Sets]] — 内置基组选择
- [[Gaussian_Input_Format]] — 自定义基组段落的位置

## 来源

- `src/gaussian_lsp/server.py` — _append_basis_diagnostics, ECP_BASIS_MARKERS
