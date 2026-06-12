# Diagnostic Engine v1

> 类型：概念
> 学科/领域：LSP 架构

## 定义

Diagnostic Engine v1 是 gaussian-lsp 的诊断序列化标准，定义了从 LSP 内部诊断到 agent 可消费 JSON 的转换契约。

## 核心机制

### 严重性策略

| 严重性 | 语义 | 阻塞 |
|--------|------|------|
| `error` | 高置信度问题，上游 runtime 大概率拒绝输入 | 是 |
| `warning` | 可疑输入，可能有意为之，不自动阻塞 | 视情况 |
| `information` | 风格或文档提示 | 否 |
| `hint` | 优化建议 | 否 |

### 7 大分类

| 分类 | 说明 | 示例 |
|------|------|------|
| `syntax` | 输入结构格式错误 | 缺少空行分隔 |
| `schema` | 缺少必需段落或段落顺序错误 | 缺少 route section |
| `type/value` | 值类型或范围错误 | %mem 格式错误 |
| `cross-file reference` | 文件引用无效 | 检查点文件路径 |
| `semantic consistency` | 化学或逻辑不一致 | 电荷/多重度电子数不匹配 |
| `preflight/runtime-risk` | 可能导致运行时失败 | 原子间距过近 |
| `style/deprecation` | 非惯用或已弃用 | 最低打印级别建议 |

### Rich Diagnostic 形状
每个 agent-facing 诊断包含：code、severity、category、confidence (0-1)、source、range、software、file_type、path、expected、actual、manual_ref、fix_hints、blocking。

### 类别推断逻辑
类别从诊断的来源 provider 和触发条件自动推断，无需手动标注。

### 序列化路径
```
LSP Diagnostic → diagnostic_to_dict() → agent_check_payload()
```

## 应用场景

- AI agent 在编辑-检查循环中消费结构化诊断
- CI 管道中对 Gaussian 输入做 gate check
- [[Diagnostics_Rule_Catalog]] 的技术基础

## 相关概念

- [[Diagnostics_Rule_Catalog]] — 所有规则的完整目录
- [[Agent_API_Reference]] — 通过 API 获取诊断快照
- [[Provider_Architecture]] — Provider 层如何生成诊断

## 来源

- `docs/DIAGNOSTIC_ENGINE_V1.md` — 规范文档
- `src/gaussian_lsp/rich_diagnostics.py` — 序列化实现
- `diagnostics/diagnostic-engine-v1.schema.json` — JSON Schema
