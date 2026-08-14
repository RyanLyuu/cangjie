---
name: resolve-cangjie-types
description: Resolve Java schema type occurrences through the x2cangjie v2 two-phase JSONL protocol, using read-only LSP/web observations and explicit target-fact or LLM decisions before materializing final Cangjie targets. Use after Java schema extraction, before skeleton generation, when reviewing unresolved fields/parameters/returns/inheritance/interfaces/generic parameters, or when an external MCP host must execute type research requests.
---

# Resolve Cangjie Types

Use `TypeResolutionCore` as the only decision engine. Keep Java sources read-only. Exchange v2 JSONL events through CLI, this Skill's script, or an MCP host.

## Load References Selectively

- Read [references/nullability-and-option.md](references/nullability-and-option.md) for `null`, nullable annotations, `Optional`, `Option`, `Some`, and `None`.
- Read [references/generic-constraints.md](references/generic-constraints.md) for bounds, wildcards, raw types, variance, and target constraints.
- Read [references/Collection.md](references/Collection.md) for arrays, lists, maps, sets, iterators, ordering, and collection mutability.
- Read [references/nemeric.md](references/nemeric.md) for numeric widths, promotions, conversions, overflow, `Rune`, `BigInt`, and `Decimal`.
- Read [references/string.md](references/string.md) for `String`, `Rune`, UTF-8/UTF-16 gaps, indexing, encoding, and interpolation.
- Read [references/extend.md](references/extend.md) for inheritance, interfaces, `open`, `override`, `redef`, and extensions.
- Read [references/function_interface.md](references/function_interface.md) for function types, SAM interfaces, lambdas, closures, and captures.
- Read [references/mutable.md](references/mutable.md) for `let`, `var`, initialization, constructors, copying, and aliasing.
- Read [references/overload.md](references/overload.md) for overload identity, constructors, named/default parameters, and call resolution.
- Read [references/exception.md](references/exception.md) for exceptions, `throw`, `try`, `catch`, resources, and Java `throws` gaps.
- Read [references/enum.md](references/enum.md) for constructors, payloads, algebraic data types, patterns, and exhaustive `match`.

Load only references selected by `resolution.retrieval_route.topics`. Preserve cited Corpus sources in observation evidence.

Map route topics directly: `nullability` to `nullability-and-option.md`; `generic` to `generic-constraints.md`; `collection` or `array` to `Collection.md`; `numeric` to `nemeric.md`; `inheritance` to `extend.md`; and `functional-interface` to `function_interface.md`. For `project-type`, inspect the Java definition through LSP. For `target-api`, use authoritative target API search and then load only the reference matching the observed API category.

## Run The Protocol

### 1. Analyze

Run without `--apply`:

```bash
python3 resolve-cangjie-types/scripts/resolve_types.py \
  --project <project> \
  --model <schema-namespace> \
  --temperature <temperature> \
  --suffix <suffix> \
  --output-dir /tmp/<project>-types
```

Read:

- `occurrences.jsonl`: field, parameter, return, body type, superclass, interface, and generic-parameter occurrences.
- `tool_requests.jsonl`: read-only work for external LSP or Web channels.
- `resolutions.jsonl`: resolved source facts and unresolved complex occurrences.
- `events.jsonl`: the complete shared protocol stream.

Do not run LSP, Web, an LLM, or a compiler inside Core.

For each resolution, read structured Java facts before doing research:

- `source_facts.nullable=true`: nullable source evidence exists.
- `source_facts.nullable=false`: an explicit non-null contract exists.
- `source_facts.nullable=null`: nullability is unknown or not applicable; use `source_facts.nullability` to distinguish them.
- `retrieval_route.topics`: exact reference topics selected from source facts.
- `retrieval_route.channels`: external channels required for this occurrence; resolved source facts use an empty list.

Do not derive routing by parsing `usage_requirements`. Those strings are downstream translation constraints.

### 2. Execute Tool Requests Externally

Route each request by its exact `channel`:

- Send `channel=lsp` only to a Java language-server MCP tool.
- Send `channel=web` only to authoritative Cangjie/API documentation search.

Use `tool_request.route_topics` to load references and specialize the query. It is copied from the occurrence's structured retrieval route.

Return observations as JSONL:

```json
{"protocol_version":"2.0","kind":"tool_observation","tool_observation":{"observation_id":"obs-1","request_id":"req-1","occurrence_id":"occ-1","channel":"web","payload":{"title":"HashMap API"},"evidence":[{"evidence_id":"ev-1","kind":"target-api","detail":"HashMap<K,V> exists in std.collection","source":"CangjieCorpus","confidence":"high"}]}}
```

Do not put Web output in an LSP observation or vice versa. Keep `request_id`, `occurrence_id`, and `channel` unchanged.

### 3. Decide Explicitly

Add one decision for each complex occurrence that has enough facts:

```json
{"protocol_version":"2.0","kind":"resolution_decision","resolution_decision":{"occurrence_id":"occ-1","target":{"type":"HashMap<Any, String>","imports":["import std.collection.HashMap"]},"authority":"target-fact","reasoning":"Target API and source usage establish the representation","usage_requirements":["preserve-map-lookup-semantics"],"translation_guidance":["Translate map operations through HashMap APIs."],"evidence_ids":["ev-1"]}}
```

Use `authority=target-fact` only with cited observation evidence. Use `authority=llm` for an explicit model judgment; include reasoning and occurrence-local guidance. Never turn an occurrence decision into a global mapping rule.

For a bounded parameter, put the complete finalized declaration in `target.type`, for example `T where T <: Base`. Skeleton splits the parameter name from the `where` clause and never reconstructs the bound from Java text.

Leave the occurrence unresolved when target facts and an LLM decision are both absent. An observation alone never resolves a type.

### 4. Finalize And Materialize

Combine observation and decision events in one JSONL file, then run:

```bash
python3 resolve-cangjie-types/scripts/resolve_types.py \
  --project <project> \
  --model <schema-namespace> \
  --temperature <temperature> \
  --suffix <suffix> \
  --events-in <events.jsonl> \
  --apply
```

Run skeleton generation only when the summary reports zero unresolved occurrences. Skeleton generation fails closed on missing or unresolved `target.type`.

## Respect The Boundary

- Resolve primitives, common scalar built-ins, arrays of resolved scalar types, project types, and generic parameter names only from bundled source/target facts.
- Treat collections, functional interfaces, wildcards, bounded generics, and external APIs as complex until a decision supplies `target.type`.
- Preserve Java nullability and type shape in `source_facts`; do not run an independent target nullability or constraint solver.
- Select retrieval references from `retrieval_route`, never from free-form reasoning or compatibility strings.
- Mirror source nullability and generic bounds into `usage_requirements` only for Translator constraints.
- Put usage constraints in `usage_requirements` and actionable method-body advice in `translation_guidance`.
- Keep LSP and Web requests read-only.
- Do not enumerate candidates, consult deleted mapping tables, erase wildcards to `Any`, generate shims, run Cangjie probes, or repair compilation failures here.
- Do not let Skeleton or Translator recompute a type. Skeleton reads `resolution.target.type`; Translator reads the same record's requirements and guidance.

## Complete The Run

Verify that:

- every schema type occurrence has one stable ID and one resolution record;
- class `extends`, `implements`, and class/method generic parameters are included;
- every external observation matches a generated request and channel;
- every `target-fact` decision cites observed evidence;
- unresolved records have `target: null`;
- all materialized resolved slots contain `resolution.status=resolved` and `resolution.target.type`;
- repeated runs produce byte-identical occurrence, request, resolution, and event JSONL files;
- no Java source file changed.
