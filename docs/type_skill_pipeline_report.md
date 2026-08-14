# Java 到 Cangjie 类型阶段 v2 实现报告

## 结果

类型阶段已从“直接映射 + 独立 nullability 推断 + override”重构为两阶段事件协议。

```text
schema
  -> occurrences
  -> structured SourceFacts
  -> RetrievalRoute
  -> analyze
  -> resolved source facts + read-only ToolRequests
  -> external LSP/Web observations
  -> target-fact or LLM decisions
  -> finalize
  -> schema materialization
  -> strict skeleton
  -> guidance-aware translator
```

## 模块

| 模块 | 职责 |
| --- | --- |
| `models.py` | v2 occurrence、request、observation、decision、resolution 合同 |
| `core.py` | 纯两阶段状态机 |
| `protocol.py` | JSONL 解析与输出 |
| `schema_adapter.py` | occurrence 提取与 resolution 物化 |
| `service.py` | 项目 I/O 和稳定运行产物 |
| `cli.py` | CLI 入口 |
| `mcp_facade.py` | MCP host 的薄 facade |
| `adapter.py` | 禁用旧全局 mapper 的兼容面 |

Skill 脚本调用同一个 CLI，因此三种入口不会产生不同决策实现。

## 运行产物

```text
data/java/type_resolution_runs/<project>/<model>/<temperature+suffix>/
  occurrences.jsonl
  tool_requests.jsonl
  resolutions.jsonl
  events.jsonl
  summary.json
  manifest.json
```

前四个 JSONL 使用稳定排序和紧凑编码；时间戳只存在于非稳定性验收范围外的 `summary.json`。

## 行为变化

- `Map<Object,String>`、`Callable<Boolean>`、wildcard、外部 API 等复杂类型不再由旧映射表自动确定。
- 未决记录使用 `status=unresolved,target=null`。
- Java null 证据保存在 `source_facts.nullable` 布尔三态和 `source_facts.nullability` 状态中。
- nullability、collection、generic、functional-interface 等检索主题由结构化 `retrieval_route` 决定，不解析 usage requirement 字符串。
- `usage_requirements` 继续向 Translator 传递约束；只有内置目标事实或显式 decision 才决定最终 optional spelling。
- 父类、接口、类泛型和方法泛型进入统一 occurrence 模型。
- Skeleton 缺少 resolved target 时失败，不再 fallback。
- Translator 从相同 resolution 注入 requirements 和 guidance。
- 编译验证的 overload 匹配读取已物化参数 target，不再调用 mapper。

## 使用

分析：

```bash
python3 resolve-cangjie-types/scripts/resolve_types.py \
  --project jansi --model deepseek-chat --temperature 0.0 \
  --output-dir /tmp/jansi-types
```

外部 MCP 执行 `tool_requests.jsonl` 后，把 `ToolObservation` 与 `ResolutionDecision` 写入同一事件文件。

物化：

```bash
python3 resolve-cangjie-types/scripts/resolve_types.py \
  --project jansi --model deepseek-chat --temperature 0.0 \
  --events-in /tmp/jansi-events.jsonl --apply
```

只有 `summary.resolution_status.unresolved` 为零时才进入 skeleton 阶段。

## 验证

`tests/test_type_resolution.py` 覆盖：

- 简单事实自动解析；
- 复杂类型保持 unresolved；
- LSP/Web request 隔离且只读；
- observation 不自动定型；
- decision 与 evidence 校验；
- 类级和泛型 occurrence 物化；
- Skeleton fail-closed；
- Translator guidance 读取；
- CLI/MCP 共用 service；
- JSONL 字节级稳定；
- `nullable=true/false/null` 与结构化检索路由。
