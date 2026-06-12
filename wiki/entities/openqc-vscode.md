# OpenQC VS Code Extension

> 类型：框架
> 创建日期：2026-06-12
> 来源数：2

## 简介

OpenQC-VSCode (`newtontech/OpenQC-VSCode`) 是 gaussian-lsp 在 VS Code 中的集成层。两者必须保持行为一致。

## 对齐要求

### 文件扩展名
- `.gjf` — Gaussian input file
- `.com` — Gaussian command file

### 诊断对齐
- Diagnostics 和 severity 级别必须一致
- 涵盖：无效 route、几何块、ModRedundant 段落、ONIOM 层

### 补全对齐
- 方法、基组、job type 和常用关键词的补全词汇表必须同步
- 词汇来源：gaussian-lsp 的 parser vocabulary

### 解析器 Fixtures
- 最小化 parser fixtures 用于冒烟测试
- 有效的和无效的输入样本

## 发布检查流程

在 OpenQC 公开发布之前，必须：

1. 用 **一个有效** Gaussian 输入文件对本服务器和扩展做冒烟测试
2. 用 **一个无效** Gaussian 输入文件做同样的冒烟测试
3. 确认两端行为一致

## 相关来源

- `docs/OPENQC_ALIGNMENT.md` — 对齐文档
- `src/gaussian_lsp/server.py` — LSP 服务器实现

## 相关实体/概念

- [[Gaussian_Input_Format]] — 输入文件格式
- [[Agent_API_Reference]] — Agent 可用的 API
- [[Provider_Architecture]] — LSP 功能提供者架构

## 历史更新

- 2026-06-12: 初始创建
