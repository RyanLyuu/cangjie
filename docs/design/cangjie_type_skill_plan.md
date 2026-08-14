# Cangjie Type Resolution v2

## 设计结论

类型阶段采用一个核心、三种入口：

```text
CLI ───┐
Skill ─┼─> JSONL v2 ─> TypeResolutionCore ─> JSONL v2
MCP ───┘
```

`TypeResolutionCore` 是纯两阶段状态机，不访问网络、LSP、LLM 或编译器。CLI、Skill 脚本和 MCP facade 只负责输入输出相同协议。

## 两阶段状态机

第一阶段 `analyze`：

1. 从 schema 提取 occurrence。
2. 生成结构化 `SourceFacts`，包括 `nullable: true/false/null`、类型形态和源证据。
3. 从 `SourceFacts` 确定 `RetrievalRoute`，不解析字符串标签。
4. 只用明确内置事实解析 primitive、常用 scalar、已解析元素的数组、项目类型和泛型参数名。
5. 按 route 为复杂类型生成只读 `ToolRequest`。
6. 输出 resolved 或 unresolved 记录。

第二阶段 `finalize`：

1. 校验 `ToolObservation` 是否对应已生成 request，且 LSP/Web 通道一致。
2. 接受 occurrence-specific `ResolutionDecision`。
3. `target-fact` 决策必须引用 observation evidence；`llm` 决策必须显式给出 target 和 reasoning。
4. 没有目标事实或 LLM 决策时保持 unresolved。

Observation 只增加事实，不会自动产生目标类型。

## 数据合同

每行事件包含：

```json
{"protocol_version":"2.0","kind":"tool_request","tool_request":{}}
```

事件种类：

- `occurrence`
- `tool_request`
- `tool_observation`
- `resolution_decision`
- `resolution`

最终 resolution 的权威字段：

```json
{
  "status": "resolved",
  "target": {"type": "String", "imports": []},
  "source_facts": {
    "nullable": null,
    "nullability": "unknown",
    "reference_type": true
  },
  "retrieval_route": {
    "topics": ["nullability"],
    "channels": []
  },
  "usage_requirements": ["source-nullability-unknown"],
  "translation_guidance": [],
  "decision_authority": "source-fact"
}
```

`nullable` 是布尔三态：`true` 表示存在可空证据，`false` 表示存在明确非空契约，`null` 表示未知或不适用。`nullability` 进一步区分 `unknown` 和 `not-applicable`。检索路由只读取 `source_facts`；`usage_requirements` 是 Translator 的兼容约束，不是路由输入。

## Occurrence 范围

- 字段类型
- 参数类型
- 返回类型
- 方法体类型
- 父类
- 实现接口
- 类泛型参数
- 方法泛型参数

有界泛型参数属于复杂 occurrence。最终 `target.type` 使用完整目标声明，例如 `T where T <: Base`；Skeleton 仅拆分并渲染该最终声明，不从 Java bound 猜测目标约束。

ID 由 schema 文件、class、fragment、variation 和 identifier 确定，重跑稳定。

## 下游合同

物化时完整记录写入 `type_translations.*.*.resolution`。旧的 `translated_target_type` 只是 resolved target 的镜像。

Skeleton：

- 只读取 `resolution.status=resolved` 的 `target.type`。
- 缺失或 unresolved 时立即失败。
- 不调用全局类型表，不根据字符串猜类型或 import。

Translator：

- 读取同一 resolution 的 `usage_requirements`。
- 读取同一 resolution 的 `translation_guidance`。
- 不修改冻结签名，不重新映射类型。

外部检索 Host：

- 读取 `retrieval_route.topics` 和 `ToolRequest.route_topics` 选择 nullability、collection、generic、functional-interface 等资料。
- 读取 `retrieval_route.channels`，严格隔离 LSP 与 Web。

## 非目标

- 候选枚举或排序
- wildcard 擦除
- 独立 nullability 决策器
- 泛型约束求解
- shim 生成
- Cangjie probe
- 编译 repair
- 基于旧映射表的 fallback

## 验收条件

1. Core 不执行外部工具。
2. LSP/Web request 与 observation 通道隔离。
3. Observation 无 decision 时复杂类型仍 unresolved。
4. 父类、接口和泛型参数进入 occurrence 与物化层。
5. Skeleton 只消费最终 `target.type`。
6. Translator 消费 requirements/guidance。
7. 四个 JSONL 产物字节级稳定。
8. Java 源码保持只读。
