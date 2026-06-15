# Gaussian Runtime Log Errors

> 类型：概念
> 创建日期：2026-06-15
> 学科/领域：量子化学 / 运行时错误诊断
> 来源：`raw/assets/gaussian-output-format.md`, cclib `gaussianparser.py`, Gaussian 16 用户手册

## 定义

Gaussian 16 程序由一系列顺序执行的内部 Link 可执行文件（l1, l101, l103, l202, l301, l402, l502, l716, l9999 等）组成。每个 Link 负责一类计算任务，失败时通过 supervisor `Lnk1e` 报告致命终止。本概念文档记录 LSP 后端解析这些运行时错误的规则集（issue #87）。

## 错误模式

### GAUSS-E034：SCF 收敛失败

```
SCF Done:  E(RHF) = -74.96 A.U. after  50 cycles
Convergence failure -- SCF cycle limit reached.
Error termination via Lnk1e in /scr1/g16/l502.exe at <date>.
```

- 触发：`Convergence failure` 或 `SCF fails to converge`
- 关联 Link：l502（SCF 迭代）
- 修复建议：`scf=(xqc, maxcycle=128)`、改进初始猜测、增大积分格

### GAUSS-E035：几何/Z-matrix 解析失败

```
Error in geometry specification.
Stop in parsing Z-matrix.
Error termination via Lnk1e in /scr1/g16/l402.exe at <date>.
```

- 触发：`Error in geometry` / `Input Error` / `Stop in parsing`
- 关联 Link：l101（标题/电荷/多重度）、l402（Z-matrix）
- 修复建议：校核电荷/多重度行、切换到笛卡尔输入

### GAUSS-E036：致命终止标记

```
Error termination via Lnk1e in /scr1/g16/l502.exe at <date>.
```

- 触发：`Error termination via` supervisor 行
- 含义：Gaussian 监督进程报告作业失败终止
- 通常与 GAUSS-E037 一起出现（结构化的 Link 故障）

### GAUSS-E037：Link 级故障（结构化）

`parse_log()` 从 supervisor 行提取 Link 编号并通过 `LINK_KNOWLEDGE` 表映射到人类可读的角色、成因和修复提示。已编目的 Link：

| Link | 角色 |
|------|------|
| 101  | title/charge/multiplicity |
| 103  | geometry optimization |
| 202  | coordinate standardization |
| 301  | basis set specification |
| 402  | Z-matrix internal coordinates |
| 502  | SCF iteration |
| 716  | first derivatives |
| 9999 | termination / archive |

未在表中的 Link（例如 l666）会得到通用的 `unknown` 角色和「检查 Link 周围日志」提示。

### GAUSS-E038：几何优化步数耗尽

```
Optimization stopped.
 -- Number of steps exceeded, NStep= 50.
Error termination via Lnk1e in /scr1/g16/l9999.exe at <date>.
```

- 触发：`Optimization stopped` 或 `Number of steps exceeded`
- 关联 Link：l103（优化）、l9999（归档）
- 修复建议：增大 `opt=MaxCycle`、`opt=calcfc`、定期刷新 Hessian

### GAUSS-E039：内存/磁盘耗尽

```
Not enough memory to allocate work array 1 of length 12345678.
Wanted    4096000000 bytes of mem, got   536870912 bytes.
```

- 触发：`Not enough memory` / `insufficient memory` / `Wanted ... bytes of mem`
- 关联 Link：通常 l502，但也可能在任意需要大块分配的 Link 中
- 修复建议：提高 `%mem`、切换到 `scf=direct`、按 N^4 缩放评估

### GAUSS-W034：优化步未收敛（非致命）

```
Item               Value     Threshold  Converged?
Maximum Force       0.000144   0.000450   NO
```

- 触发：`Item ... NO` 单行（位于 Berny 优化每一步）
- 含义：本步未满足收敛标准，但是非致命警告
- 如果后续没有 `Optimization completed` 则升级为致命

### GAUSS-I031：日志截断

- 触发：日志中既没有 `Normal termination` 也没有 `Error termination`
- 含义：日志可能被截断或不完整
- 修复建议：重新获取完整日志

## DiagnosticEnvelope/v1 字段映射

每条规则输出携带以下结构化字段（与 `preflight.py` 一致）：

| 字段 | 内容 |
|------|------|
| `code` | `GAUSS-Exxx` / `GAUSS-Wxxx` / `GAUSS-Ixxx` |
| `severity` | error / warning / information |
| `category` | preflight/runtime-risk / syntax / semantic consistency |
| `blocking` | 致命错误为 True；W034 和 I031 为 False |
| `confidence` | 0.6（I031）到 0.99（E036 supervisor 行） |
| `facts` | 结构化字段（link_number, link_role, nstep, last_cycles 等） |
| `fix_hints` | 具体修复建议（`scf=(xqc, maxcycle=128)`、`opt=calcfc` 等） |
| `actions` | 含 `safe_to_auto_apply=False` 和 `refusal_reason` 的 repair preview |
| `source_provenance` | 触发片段 + 规则 ID + 来源 |
| `manual_ref` | 指向 Gaussian 官方手册的链接 |
| `artifact_roles` | runtime-output, control, structure, link0, optimization |

## 来源

- `raw/assets/gaussian-output-format.md` — Gaussian 输出格式参考
- `raw/assets/gaussian-github-parsers.md` — cclib / gaussianparser 参考
- `src/gaussian_lsp/log_parser.py` — Python 解析器实现
- `tests/fixtures/log/` — 真实样式的运行时日志 fixtures
- https://gaussian.com/scf/ — SCF 收敛手册
- https://gaussian.com/opt/ — 优化手册
- https://gaussian.com/overlay1/ — Link 编号参考
