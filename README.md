# x2cangjie

Java-to-Cangjie project translation baseline. The repository contains the
active schema, type-resolution, skeleton MCP, and file-translation pipeline.
Preprocessed Java projects are stored under
`projects/cleaned_final_projects_evosuite_cleaned_base/`.

## Requirements

- Python environment from `environment.yaml`
- JDK 11, Maven, and `jdeps`
- Cangjie SDK 1.0.5 with `cjc` and `cjpm` on `PATH`
- Node.js/npm and an authenticated Codex CLI

Initialize the Cangjie SDK and authenticate Codex before running:

```bash
source /path/to/cangjie/envsetup.sh
codex login
```

## Run

The complete workflow is one command:

```bash
bash run.sh commons-fileupload
```

`run.sh` runs these stages in order:

1. Generate occurrence-aware Java schemas.
2. Extract class and file dependencies.
3. Resolve types, call the skeleton MCP tool, and compile the TODO skeleton.
4. Translate files in dependency order with one persistent Codex app-server
   session and incremental `cjpm build` validation.

The default settings are:

```text
schema model:       codex-baseline
temperature:        0.0
project suffix:     _evosuite_cleaned_base
project root:       projects/cleaned_final_projects_evosuite_cleaned_base
translate tests:    false
agent transport:    app-server
max agent builds:   3
file watchdog:      300 seconds
```

The defaults can be overridden with environment variables without changing the
command shape:

```bash
SCHEMA_MODEL=my-schema MAX_BUILDS=2 bash run.sh commons-cli
```

The pipeline writes schemas, skeletons, translations, receipts, and logs under
`data/`. These are runtime artifacts and are ignored by Git. Each translation
file is handled in an isolated project-only workspace. The agent owns edits and
up to three `cjpm build` attempts; if the file still fails validation or reaches
the 300-second watchdog, the controller restores its original TODO skeleton and
records a fallback.

For focused debugging, the individual stage scripts remain available under
`scripts/java/`: `create_schema.sh`, `get_dependencies.sh`,
`create_skeleton.sh`, and `translate_fragment.sh`.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -q
```
