# Type Resolution v2 典型输入输出

本例展示 `Map<String, String>` 字段如何从 `unresolved` 变为 `resolved`，并最终进入 Skeleton 和 Translator。

> 实际协议文件采用 JSONL，每条事件占一行。本文将事件展开为格式化 JSON，便于阅读。示例 ID 也经过缩短；真实 ID 由系统生成稳定 hash。

## 流程概览

```text
Java Schema
    |
    v
TypeOccurrence
    |
    v
SourceFacts
    |
    v
RetrievalRoute
    |
    +-- LSP ToolRequest ----> 外部 Java LSP
    |
    +-- Web ToolRequest ----> 外部文档检索
                                |
                                v
                          ToolObservation
                                |
                                v
                       ResolutionDecision
                                |
                                v
                            finalize
                                |
                  +-------------+-------------+
                  |                           |
                  v                           v
              Skeleton                   Translator
```

## 输入

### Java 字段

```java
import java.util.Map;

class Demo {
    private Map<String, String> lookup;
}
```

### Schema 中提取的 occurrence

完整 Schema 很大，本例只展示类型阶段实际需要的字段：

```json
{
  "occurrence_id": "occ-map",
  "source_path": "projects/demo/src/main/java/example/Demo.java",
  "symbol": "Demo.lookup",
  "role": "field",
  "source_type": "Map<String, String>",
  "source_fqn": "java.util.Map",
  "start_line": 4
}
```

## Analyze 输出

Analyze 阶段生成四个稳定 JSONL 文件：

| 文件 | 内容 | 本例中的结果 |
| --- | --- | --- |
| `occurrences.jsonl` | 从 Schema 提取的类型出现点 | `occ-map` |
| `tool_requests.jsonl` | 等待外部执行的只读请求 | 一个 LSP 请求和一个 Web 请求 |
| `resolutions.jsonl` | 当前阶段的类型解析结果 | `status=unresolved, target=null` |
| `events.jsonl` | 上述事件的统一事件流 | occurrence + requests + resolution |

因此，Analyze 阶段的最终产物是：

```text
一个 unresolved Resolution
+
两个等待外部执行的 ToolRequest
```

### 结构化源事实与检索路由

Core 先保留 Java 侧事实，再确定检索主题。`nullable` 是布尔三态：`true` 表示有可空证据，`false` 表示有明确非空契约，`null` 表示未知或不适用；本例的 `nullability=unknown` 表明这里是未知。

```json
{
  "source_facts": {
    "nullable": null,
    "nullability": "unknown",
    "primitive": false,
    "reference_type": true,
    "array": false,
    "generic": true,
    "wildcard": false,
    "external": true,
    "project_type": false,
    "type_parameter": false,
    "bounded_type_parameter": false,
    "collection_like": true,
    "functional_interface_like": false,
    "binding_mutable": null,
    "nullability_conflict": false,
    "operations": [],
    "evidence": []
  },
  "retrieval_route": {
    "topics": [
      "nullability",
      "collection",
      "generic",
      "target-api"
    ],
    "channels": [
      "lsp",
      "web"
    ],
    "reasons": [
      "source_facts.nullability=unknown",
      "source_facts.collection_like=true",
      "source type contains generic, wildcard, or bound structure",
      "no deterministic target fact resolved this occurrence"
    ]
  }
}
```

#### Nullability 三态与路由对照

下表只比较源事实如何影响 `nullability` 检索主题；是否生成 LSP/Web 请求还取决于该 occurrence 能否由内置事实直接解析。

| Java occurrence | `nullable` | `nullability` | 主要证据 | 加载 `nullability` topic |
| --- | --- | --- | --- | --- |
| `@Nullable String value` | `true` | `nullable` | 显式 nullable 注解 | 是 |
| `@NonNull String value` | `false` | `non-null` | 显式 non-null 契约 | 否 |
| `String value` | `null` | `unknown` | 无足够证据 | 是 |
| `int value` | `null` | `not-applicable` | primitive | 否 |
| 同时存在 nullable 与 non-null 证据 | `null` | `unknown` | `nullability_conflict=true` | 是，保持 fail-closed |

因此不能只看 `nullable=null`：路由器必须同时读取 `nullability` 和 `nullability_conflict`。`usage_requirements` 只是向 Translator 提供兼容约束，不参与这一步判断。

`Map<String, String>` 是复杂类型，Core 不使用旧映射表猜测结果。外部 Host 直接读取 `retrieval_route`，不从 `usage_requirements` 反向猜路由。Core 生成以下两个相互独立的只读请求。

### LSP 请求

```json
{
  "protocol_version": "2.0",
  "kind": "tool_request",
  "tool_request": {
    "request_id": "req-lsp-map",
    "occurrence_id": "occ-map",
    "channel": "lsp",
    "operation": "hover-definition",
    "query": {
      "source_path": "projects/demo/src/main/java/example/Demo.java",
      "line": 4,
      "source_type": "Map<String, String>",
      "source_fqn": "java.util.Map",
      "route_topics": [
        "nullability",
        "collection",
        "generic",
        "target-api"
      ]
    },
    "route_topics": [
      "nullability",
      "collection",
      "generic",
      "target-api"
    ],
    "read_only": true
  }
}
```

### Web 请求

```json
{
  "protocol_version": "2.0",
  "kind": "tool_request",
  "tool_request": {
    "request_id": "req-web-map",
    "occurrence_id": "occ-map",
    "channel": "web",
    "operation": "target-api-search",
    "query": {
      "source_type": "java.util.Map",
      "question": "Find authoritative Cangjie target type/API facts; do not infer a mapping.",
      "route_topics": [
        "nullability",
        "collection",
        "generic",
        "target-api"
      ]
    },
    "route_topics": [
      "nullability",
      "collection",
      "generic",
      "target-api"
    ],
    "read_only": true
  }
}
```

### 分析阶段的最终 Resolution

`resolutions.jsonl` 此时记录的是阶段性最终结果，而不是成功映射：

```json
{
  "protocol_version": "2.0",
  "kind": "resolution",
  "resolution": {
    "resolution_id": "res-map-unresolved",
    "occurrence_id": "occ-map",
    "symbol": "Demo.lookup",
    "source_type": "Map<String, String>",
    "source_fqn": "java.util.Map",
    "role": "field",
    "status": "unresolved",
    "target": null,
    "source_facts": {
      "nullable": null,
      "nullability": "unknown",
      "primitive": false,
      "reference_type": true,
      "array": false,
      "generic": true,
      "wildcard": false,
      "external": true,
      "project_type": false,
      "type_parameter": false,
      "bounded_type_parameter": false,
      "collection_like": true,
      "functional_interface_like": false,
      "binding_mutable": null,
      "nullability_conflict": false,
      "operations": [],
      "evidence": []
    },
    "retrieval_route": {
      "topics": [
        "nullability",
        "collection",
        "generic",
        "target-api"
      ],
      "channels": [
        "lsp",
        "web"
      ],
      "reasons": [
        "source_facts.nullability=unknown",
        "source_facts.collection_like=true",
        "source type contains generic, wildcard, or bound structure",
        "no deterministic target fact resolved this occurrence"
      ]
    },
    "usage_requirements": [
      "source-nullability-unknown"
    ],
    "translation_guidance": [],
    "request_ids": [
      "req-lsp-map",
      "req-web-map"
    ],
    "observation_ids": [],
    "decision_authority": "",
    "reasoning": ""
  }
}
```

这就是进入外部工具阶段前，Analyze 的完整交付边界。

## 外部工具回填

### ToolObservation

外部 MCP host 执行 Web 请求后，回填目标 API 事实：

```json
{
  "protocol_version": "2.0",
  "kind": "tool_observation",
  "tool_observation": {
    "observation_id": "obs-map",
    "request_id": "req-web-map",
    "occurrence_id": "occ-map",
    "channel": "web",
    "payload": {
      "api": "std.collection.HashMap"
    },
    "evidence": [
      {
        "evidence_id": "ev-map",
        "kind": "target-api",
        "detail": "HashMap<K,V> is available and String satisfies its key constraints",
        "source": "Cangjie API",
        "confidence": "high"
      }
    ]
  }
}
```

Observation 只提供事实，不会自动决定目标类型。因此此时 occurrence 仍然是 `unresolved`。

### ResolutionDecision

Agent 根据源码用法和目标 API 事实提交显式决策：

```json
{
  "protocol_version": "2.0",
  "kind": "resolution_decision",
  "resolution_decision": {
    "occurrence_id": "occ-map",
    "target": {
      "type": "HashMap<String, String>",
      "imports": [
        "import std.collection.HashMap"
      ]
    },
    "authority": "target-fact",
    "reasoning": "Target API evidence and source usage establish the representation",
    "usage_requirements": [
      "preserve-map-lookup-semantics"
    ],
    "translation_guidance": [
      "Translate Java map operations through HashMap APIs."
    ],
    "evidence_ids": [
      "ev-map"
    ]
  }
}
```

将 Observation 和 Decision 事件放入 `events-in.jsonl` 后执行：

```bash
python3 resolve-cangjie-types/scripts/resolve_types.py \
  --project demo \
  --model deepseek-chat \
  --temperature 0.0 \
  --events-in events-in.jsonl \
  --apply
```

## 最终输出

### Resolution

`resolutions.jsonl` 中产生最终记录：

```json
{
  "protocol_version": "2.0",
  "kind": "resolution",
  "resolution": {
    "resolution_id": "res-map",
    "occurrence_id": "occ-map",
    "symbol": "Demo.lookup",
    "source_type": "Map<String, String>",
    "source_fqn": "java.util.Map",
    "role": "field",
    "status": "resolved",
    "target": {
      "type": "HashMap<String, String>",
      "imports": [
        "import std.collection.HashMap"
      ]
    },
    "source_facts": {
      "nullable": null,
      "nullability": "unknown",
      "primitive": false,
      "reference_type": true,
      "array": false,
      "generic": true,
      "wildcard": false,
      "external": true,
      "project_type": false,
      "type_parameter": false,
      "bounded_type_parameter": false,
      "collection_like": true,
      "functional_interface_like": false,
      "binding_mutable": null,
      "nullability_conflict": false,
      "operations": [],
      "evidence": []
    },
    "retrieval_route": {
      "topics": [
        "nullability",
        "collection",
        "generic",
        "target-api"
      ],
      "channels": [
        "lsp",
        "web"
      ],
      "reasons": [
        "source_facts.nullability=unknown",
        "source_facts.collection_like=true",
        "source type contains generic, wildcard, or bound structure",
        "no deterministic target fact resolved this occurrence"
      ]
    },
    "usage_requirements": [
      "source-nullability-unknown",
      "preserve-map-lookup-semantics"
    ],
    "translation_guidance": [
      "Translate Java map operations through HashMap APIs."
    ],
    "evidence": [
      {
        "evidence_id": "ev-map",
        "kind": "target-api",
        "detail": "HashMap<K,V> is available and String satisfies its key constraints",
        "source": "Cangjie API",
        "confidence": "high"
      }
    ],
    "request_ids": [
      "req-lsp-map",
      "req-web-map"
    ],
    "observation_ids": [
      "obs-map"
    ],
    "decision_authority": "target-fact",
    "reasoning": "Target API evidence and source usage establish the representation"
  }
}
```
