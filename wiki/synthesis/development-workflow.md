# Development Workflow

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：4

## 核心论点

本文档汇总 gaussian-lsp 的开发环境设置、测试命令、质量门禁和 PR 审查流程，为贡献者和 AI agent 提供一站式参考。

## 环境设置

```bash
# 克隆并安装
git clone https://github.com/newtontech/gaussian-lsp.git
cd gaussian-lsp
pip install -e ".[dev]"

# TypeScript 依赖
npm ci
```

### 替代 Python 环境（不影响项目环境）
```bash
uv run --with pytest --with pytest-asyncio --with pytest-cov python -m pytest
```

## 测试命令

| 命令 | 说明 |
|------|------|
| `python -m pytest` | Python 测试套件 |
| `npm run test:ts` | TypeScript 测试 |
| `npm run typecheck` | TypeScript 类型检查 |
| `npm run test:ts:coverage` | TypeScript 测试覆盖率 |

## 质量门禁

| 命令 | 工具 | 用途 |
|------|------|------|
| `black src/ tests/` | black | 代码格式化 |
| `isort src/ tests/` | isort | 导入排序 |
| `mypy src/` | mypy | 类型检查 |
| `flake8 src/ tests/` | flake8 | 代码检查 |
| `pre-commit run --all-files` | pre-commit | 全部钩子 |
| `bandit src/` | bandit | 安全扫描 |

### Make 目标

| 目标 | 说明 |
|------|------|
| `make format` | 运行 black + isort |
| `make lint` | 运行 flake8 |
| `make typecheck` | 运行 mypy |
| `make test` | 运行 pytest |
| `make check` | 运行全部检查 |

## Issue 工作流

```bash
# 从 issue 创建 worktree
scripts/start_issue_worktree.sh <issue_number>

# 实现 → 本地门禁 → PR
make check
git add -A && git commit -m "feat: ..."
git push -u origin <branch>
```

PR 必须包含 `Fixes #<issue_number>`。

## PR 审查流程

三个独立的 Codex subagent **并行**审查：

| 审查者 | 职责 |
|--------|------|
| **Agent A** | 正确性和回归风险 |
| **Agent B** | 测试和覆盖率 |
| **Agent C** | 安全和可维护性 |

### 决策规则

| 决策 | 条件 |
|------|------|
| **Merge** | 无 CRITICAL 或 HIGH 问题 |
| **Modify** | 有 HIGH 问题，修复后合并 |
| **Hold** | 有 CRITICAL 问题 |

## 覆盖率要求

- Parser 和 Server: 100%
- 整体: 80%+
- `pytest --cov=src/gaussian_lsp --cov-report=html`

## 发布检查

在发布前，用 OpenQC-VSCode 扩展做冒烟测试：
- 一个有效 Gaussian 输入
- 一个无效 Gaussian 输入
- 确认两端行为一致

详见 [[OpenQC_VSCode]]。

## 来源列表

- `AGENTS.md` — Agent 工作流指南
- `README.md` — 项目设置
- `docs/pr-review-workflow.md` — PR 审查流程
- `Makefile` — 构建目标
