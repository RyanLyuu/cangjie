# Java Preprocessing

## Purpose

This stage prepares deterministic Java project artifacts for the downstream
Agent/Skill type-resolution, skeleton, and translation stages. This document is
limited to the preprocessing needed by the current baseline.

## Prerequisites

- Python 3.11 and the packages in `environment.yaml`
- Maven 3.9.x
- JDK 8, plus JDK 11 for projects that require it
- Java Tree-sitter grammar at `misc/sitter-libs/java`, or the
  `tree_sitter_java` Python package
- Built Java Call Graph JAR at
  `misc/java-callgraph/target/javacg-0.1-SNAPSHOT-static.jar`
- `jdeps`, `jar`, `zip`, `unzip`, and `rsync`

The parser first attempts to load `tree_sitter_java`. If unavailable, it builds
`misc/parser/language.so` from grammars under `misc/sitter-libs`.

## Subject Projects

The pinned repositories and revisions are defined in
`scripts/java/download_original_projects.sh`:

```text
commons-cli
commons-codec
commons-csv
commons-exec
JavaFastPFOR
commons-fileupload
commons-graph
jansi
commons-pool
commons-validator
```

## Standard Pipeline

Download the pinned projects:

```bash
bash scripts/java/download_original_projects.sh
```

Run source preprocessing for one project:

```bash
bash scripts/java/preprocess.sh commons-fileupload
```

This performs the following operations:

1. Copies the original project and adds the Maven test-JAR plugin.
2. Rewrites identifiers that conflict with Cangjie keywords.
3. Resolves Java class/package/name conflicts required by the target layout.
4. Builds and merges the main and test JARs.
5. Generates the Java call graph.
6. Removes unsupported third-party dependencies and usages.
7. Writes the cleaned project to its configured cleaned-project directory.
   Some legacy preprocessing scripts still stage under `projects/java/`; the
   downstream readers accept that layout as a compatibility fallback.

Generate the project schema:

```bash
bash scripts/java/create_schema.sh \
  commons-fileupload preprocessing 0.0 "" projects/cleaned_final_projects
```

`create_schema.sh` retains the historical model and temperature parameters only
as output namespace components. It does not call an LLM.

Generate the class dependency graph and traversal:

```bash
bash scripts/java/get_dependencies.sh \
  commons-fileupload "" projects/cleaned_final_projects
```

## EvoSuite-Cleaned Variant

If an EvoSuite-augmented source snapshot exists, run:

```bash
bash scripts/java/preprocess_evosuite_cleaned_base.sh commons-fileupload
```

or, for a project already placed under
`projects/cleaned_final_projects_evosuite/<project>`:

```bash
bash scripts/java/preprocess_evo_cleaned.sh commons-fileupload
```

Both variants use `src/java/preprocessing/clean_evosuite_tests.py`. The cleanup
utility remains active because generated-test normalization is a preprocessing
concern, not part of the archived isolation-validation pipeline.

## Active Outputs

```text
projects/cleaned_final_projects*/<project>/
data/java/call_graphs/<project>/callgraph.txt
data/java/schemas*/<namespace>/<temperature>/<project>/*.json
data/java/dependencies*/<project>/
```

Older historical outputs under `deprecated/data/java/` are not consumed as
inputs by new experiment runs:

- type-resolution maps and per-project decisions
- Cangjie skeletons and partial translations
- translation/error-analysis snapshots

## Active Entry Points

| Command | Responsibility |
| --- | --- |
| `download_original_projects.sh` | Clone pinned subject revisions |
| `build_original_projects.sh` | Build cleaned subject projects |
| `preprocess.sh` | Run the standard preprocessing chain |
| `preprocess_evo_cleaned.sh` | Prepare an EvoSuite-cleaned source snapshot |
| `preprocess_evosuite_cleaned_base.sh` | Prepare the configured EvoSuite variant |
| `create_schema.sh` | Generate Tree-sitter schema JSON |
| `get_dependencies.sh` | Generate `jdeps` graphs and traversal |

The remaining scripts in `scripts/java/` are internal stages called by these
entry points.

Both schema and dependency commands resolve projects from
`projects/cleaned_final_projects<suffix>/<project>` by default. They accept an
explicit project-root argument and retain `projects/java/...` only as a legacy
fallback.
