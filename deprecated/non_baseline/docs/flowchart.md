```mermaid
flowchart TD
    A1["original_projects/&lt;project&gt;"] -->|add_plugin.sh<br/>复制项目+添加maven-jar-plugin| A2["automated_reduced_projects/&lt;project&gt;"]
    A2 -->|handle_keyword_conflicts.sh<br/>重命名Cangjie关键字冲突| A3["keyword_handled/&lt;project&gt;"]
    A3 -->|handle_name_conflicts.sh<br/>重命名内部类命名冲突| A3b["name_handled/&lt;project&gt;"]
    A3b -->|merge_jar.sh<br/>mvn build + 合并main/test JAR| A4["name_handled/&lt;project&gt;/target/&lt;project&gt;-merged.jar"]
    A4 -->|generate_cg.sh<br/>java-callgraph 分析merged JAR| A5["name_handled/&lt;project&gt;/callgraph.txt<br/>data/java/call_graphs/&lt;project&gt;/callgraph.txt"]
    A5 -->|reduce_third_party_libs.sh<br/>分析调用图, 移除未使用的第三方依赖| A6["cleaned_final_projects/&lt;project&gt;<br/>(含target/classes)"]
    A3b -->|源码| A6

    A6 -->|create_schema.sh<br/>tree-sitter AST解析| C1["data/java/schemas/&lt;project&gt;/*.json"]
    A5 -->|读取call graph| C1
    A6 -->|get_dependencies.sh<br/>jdeps分析+拓扑排序| C2["data/java/dependencies/&lt;project&gt;/traversal.json + dependencies.json"]

    D1["misc/CangjieCorpus/<br/>仓颉语料库(Markdown)"] -->|src/java/rag/indexer.py<br/>分块+embedding+索引| D2["data/java/rag/<br/>chromadb + bm25_index.pkl + chunks.json"]
    D3["Oracle Java API文档<br/>(java.base)"] -->|crawl_java_base.sh| D4["data/java/crawl/java.base_module_doc.json"]

    C1 -->|resolve_types.sh<br/>Codex 类型解析+契约物化| E1["data/java/type_resolution_runs/<br/>resolutions.jsonl + schema type_translations"]
    D4 --> E1

    C1 --> E2
    C2 -->|create_skeleton.sh<br/>启动 skeleton agent| S1["MCP generate_cangjie_skeleton"]
    E1 -->|读取已物化类型契约| S1
    S1 -->|生成 + cjpm build| E2["data/java/skeletons/&lt;project&gt;/<br/>(Cangjie骨架文件)"]

    C1 -->|translate_fragment.sh<br/>compositional_translation_validation.py| F1["逐片段翻译 + cjpm build 编译验证"]
    C2 -->|读取traversal顺序| F1
    E1 -->|加载类型映射| F1
    E2 -->|替换骨架TODO| F1
    D2 -->|RAG翻译增强<br/>注入API文档+语法参考<br/>编译失败时检索修复方案| F1
    F1 -->|LLM翻译| F2{"cjpm build 编译通过?"}
    F2 -->|否, 错误反馈重试| F1
    F2 -->|是| F3["更新 schema translation_status=completed<br/>更新 skeleton 替换TODO"]
    F3 -->|全部片段完成| F4["data/java/skeletons/&lt;project&gt;/src/<br/>(完整Cangjie项目)"]

    classDef input fill:#e1f5fe,stroke:#01579b
    classDef output fill:#e8f5e9,stroke:#2e7d32

    class A1,D1,D3 input
    class A2,A3,A3b,A4,A5,A6,C1,C2,D2,D4,E1,E2,F3,F4 output
```
