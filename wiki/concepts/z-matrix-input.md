# Z-Matrix Input

> 类型：概念
> 学科/领域：量子化学 / 输入格式

## 定义

Z-matrix（内坐标）是一种用键长、键角和二面角定义分子几何的方式，替代笛卡尔坐标。gaussian-lsp 支持 Z-matrix 输入的解析、诊断和导航。

## 核心机制

### Z-matrix 格式
```text
C
C  1  1.54
H  1  1.09  2  109.5
H  1  1.09  2  109.5  3  120.0
```

每行的字段数：
- 第一个原子：1 个字段（元素）
- 第二个原子：3 个字段（元素 参考原子 距离）
- 第三个原子：5 个字段（+ 参考原子 角度）
- 后续原子：7 个字段（+ 参考原子 二面角）

### 变量定义
```text
Variables:
R_CC = 1.54
R_CH = 1.09
A_HCH = 109.5
```

距离和角度值可以替换为变量名，然后在几何段落之后用 `NAME=value` 格式定义。

### LSP 诊断
- 混合笛卡尔/Z-matrix 行检测（字段数不在 {1,3,5,7} 中时报错）
- 原子参考位置必须为整数索引
- 未定义变量检测
- 无效变量定义格式检测

### LSP 导航
- **Go to Definition**: 从变量引用跳转到变量定义
- **Find References**: 查找变量的所有使用位置
- **Rename**: 安全地重命名 Z-matrix 变量（workspace edit）

## 应用场景

- 对称性分子用 Z-matrix 更自然
- 反应坐标扫描（扫描一个键长或角度）
- 需要精确定义分子内坐标

## 相关概念

- [[Gaussian_Input_Format]] — Z-matrix 在输入文件中的位置
- [[Route_Section_Syntax]] — 与 Scan job type 配合

## 来源

- `src/gaussian_lsp/server.py` — _append_zmatrix_diagnostics
- `src/gaussian_lsp/features/rename.py` — 变量重命名
- `src/gaussian_lsp/features/references.py` — 变量引用查找
- `src/gaussian_lsp/features/definition.py` — 变量定义跳转
