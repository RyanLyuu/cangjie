# x2cangjie

This repository contains the x2cangjie Java-to-Cangjie baseline. Codex resolves
occurrence-level types, Cangjie compilation validates every type and fragment,
and failed candidates deterministically return to a compilable TODO skeleton.

## Active Scope

- Java project download and build setup
- Cangjie keyword and Java name-conflict normalization
- Third-party dependency reduction
- Developer/EvoSuite test preprocessing
- Call-graph generation
- Tree-sitter schema generation
- Class dependency extraction
- Codex-backed occurrence-level type translation
- Minimal `cjc` type probes with at most three attempts
- Cangjie TODO skeleton generation and mandatory `cjpm build`
- Dependency-ordered Codex fragment translation with incremental `cjpm build`

The intended main flow is:

```text
Java preprocessing and occurrence-aware schema
  -> Codex type decisions and isolated cjc probes
  -> direct schema.type_translations materialization
  -> TODO skeleton generation and cjpm build
  -> separate dependency-ordered fragment command
```

## Quick Start

```bash
conda env create -f environment.yaml
conda activate x2cangjie

# Place preprocessed inputs under this directory before starting.
bash scripts/java/create_schema.sh \
  commons-cli codex-baseline 0.0 _evosuite_cleaned_base \
  projects/cleaned_final_projects_evosuite_cleaned_base
bash scripts/java/get_dependencies.sh \
  commons-cli _evosuite_cleaned_base \
  projects/cleaned_final_projects_evosuite_cleaned_base
bash scripts/java/create_skeleton.sh \
  commons-cli codex-baseline _evosuite_cleaned_base 0.0 false
bash scripts/java/translate_fragment.sh \
  commons-cli codex-baseline _evosuite_cleaned_base 0.0 false
```

`create_skeleton.sh` runs the complete type-to-skeleton command and exits only
after `cjpm build` succeeds. `resolve_types.sh` is the optional type-only entry
point. Both commands use the authenticated local `codex` CLI; pass a sixth
argument to select a Codex model explicitly.

Already-cleaned projects do not need preprocessing again. Regenerating them
with the preprocessing scripts requires Maven, suitable JDK versions, the Java
Tree-sitter grammar, and the `java-callgraph` fat JAR.

## Layout

```text
src/java/preprocessing/   Java source normalization and test cleanup
src/java/decomposition/   Tree-sitter project schema extraction
src/java/type_resolution/ Baseline AgentRunner, Codex adapter, probes, and schema slots
src/java/translation/     Skeleton and baseline fragment translation commands
src/java/isolation_validation/  Runtime and behavioral validation support
src/java/rag/             Translation retrieval support
src/java/progressive_kb/  Reusable verified translation examples
src/java/analysis/        Experiment and error analysis
src/java/utils/           Shared pipeline utilities
scripts/java/             Active pipeline entry points
data/java/                Call graphs, schemas, and dependency artifacts
```
