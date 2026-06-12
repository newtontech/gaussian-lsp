# Link0 Commands

> 类型：工具
> 创建日期：2026-06-12
> 来源数：3

## 简介

Link0 命令控制 Gaussian 的资源分配和文件管理。它们出现在输入文件最顶部，以 `%` 前缀。gaussian-lsp 识别 19 种 Link0 命令。

## 关键属性

### 资源管理

| 命令 | 值类型 | 说明 | 示例 |
|------|--------|------|------|
| **%mem** | memory | 内存分配 | `%mem=4GB` |
| **%nproc** | positive_int | 处理器数 | `%nproc=8` |
| **%nprocs** | positive_int | 处理器数（别名） | `%nprocs=8` |
| **%nprocshared** | positive_int | 共享内存处理器数 | `%nprocshared=4` |
| **%nprocsshared** | positive_int | 共享内存处理器数（别名） | `%nprocsshared=4` |

### 文件管理

| 命令 | 值类型 | 说明 |
|------|--------|------|
| **%chk** | path | 检查点文件 |
| **%oldchk** | path | 旧检查点文件（读取） |
| **%rwf** | path | 读写文件 |
| **%scr** | path | 临时文件目录 |
| **%int** | path | 积分文件 |
| **%d2e** | path | 二阶积分文件 |
| **%oldmatrix** | path | 旧矩阵文件 |
| **%oldraw** | path | 旧原始数据文件 |
| **%oldfc** | path | 旧力常数文件 |

### GPU 计算

| 命令 | 值类型 | 说明 |
|------|--------|------|
| **%gpu** | string | 启用 GPU 加速 |
| **%gpucards** | string | 指定 GPU 卡 |
| **%pgmcards** | string | GPU 程序卡 |

### 其他

| 命令 | 值类型 | 说明 |
|------|--------|------|
| **%kjob** | string | 作业控制 |
| **%subst** | string | 路径替换 |
| **%lindaworkers** | string | Linda 网络工作节点 |

## 安全验证

LSP 会检测 Link0 值中的不安全字符 (`;`, `|`, `&`, `$`, `` ` ``, `"`, `\`) 和控制字符（ASCII < 32），拒绝包含这些字符的值以防止注入。

## 官方参考（Gaussian 16 文档）

以下命令来自 gaussian.com/link0/ 官方文档:

| 命令 | 说明 | 默认值 |
|------|------|--------|
| `%Mem=N` | 动态内存（8字节字为单位，可加 KB/MB/GB/TB 后缀） | 800 MB |
| `%Chk=file` | 检查点文件位置 | — |
| `%OldChk=file` | 旧检查点（复制到当前 chk，不破坏原始） | — |
| `%SChk=file` | 保存检查点副本 | — |
| `%RWF=file` | 单一读写文件 | — |
| `%RWF=loc1,size1,loc2,size2,...` | 分片读写文件（跨磁盘） | — |
| `%OldMatrix=matfile` | 复制矩阵元素文件到 chk | — |
| `%OldRawMatrix=matfile` | 复制原始矩阵文件到 chk | — |
| `%Int=spec` | 双电子积分文件位置 | — |
| `%D2E=spec` | 双电子积分导数文件位置 | — |
| `%KJob L N [M]` | 在第 M 次执行 Link N 后终止 | — |
| `%Save` | 运行结束时保存临时文件 | — |
| `%ErrorSave` / `%NoSave` | 成功时删除临时文件 | — |
| `%Subst L N dir` | 使用替代 Link 可执行文件 | — |
| `%CPU=proc-list` | CPU 核列表（逗号分隔） | — |
| `%NProcShared=N` | 共享内存并行处理器数 | — |
| `%GPUCPU=gpus=cores` | GPU 到 CPU 核心绑定 | — |
| `%LindaWorkers=nodes` | Linda 网络并行节点列表 | — |
| `%UseSSH` | 使用 SSH 启动 Linda workers | rsh |

### 优先级顺序

1. Link0 输入（`%-lines`）— 最高
2. 命令行选项（`g16 -c="..."`）
3. 环境变量（`GAUSS_CDEF` 等）
4. Default.Route 文件

## 相关来源

- `src/gaussian_lsp/parser/gjf_parser.py` — LINK0_COMMANDS 列表、UNSAFE_LINK0_CHARS
- `src/gaussian_lsp/server.py` — _append_link0_value_diagnostics
- `src/gaussian_lsp/features/typecheck.py` — _LINK0_SCHEMA
- `raw/assets/gaussian-keywords-reference.md` — 官方 Link0 命令完整文档

## 相关实体/概念

- [[Gaussian_Input_Format]] — Link0 在输入文件中的位置
- [[Diagnostics_Rule_Catalog]] — G010: 未知 Link0 命令、G011: 异常 nproc、G012: 内存过低
- [[Route_Section_Syntax]] — Link0 与 route section 的分隔

## 历史更新

- 2026-06-12: 初始创建
- 2026-06-12: 扩展官方 Link0 命令参考（来源: gaussian.com/link0/）
