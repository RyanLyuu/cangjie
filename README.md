# x2cangjie

Java-to-Cangjie baseline driven by Codex and Cangjie compiler feedback.

The active Python surface is intentionally limited to preprocessing/schema
generation, baseline type resolution, skeleton MCP generation, and file-level
translation. Historical artifacts and the separately developed type-resolution
skill are intentionally excluded from this repository checkout.

## Workflow

```text
Preprocessed Java project
  -> occurrence-aware schema generation
  -> class and fragment dependency analysis
  -> Codex type resolution with isolated cjc probes
  -> Codex skeleton agent calls generate_cangjie_skeleton MCP tool
  -> compilable TODO skeleton and cjpm build
  -> dependency-ordered file translation with agent-owned cjpm repair
```

`create_skeleton.sh` stops after a dedicated Codex agent calls the local
`generate_cangjie_skeleton` MCP tool and the resulting skeleton builds
successfully. The tool rejects unresolved type contracts and writes only below
`data/java/` in the current repository.
Fragment translation is started separately with `translate_fragment.sh`. It now
assigns each dependency-ordered Java file to one persistent Codex app-server
thread, avoiding a new `codex exec/resume` process for every file. The agent
owns edits and may run at most three `cjpm build` attempts per file; the 300
second limit remains an emergency watchdog. Each run gives the agent an isolated
temporary copy containing only the selected Java project, its schemas, and its
Cangjie translation package; Codex runs with its workspace sandbox enabled and
cannot use sibling projects or repository-wide helpers. The controller
synchronizes only the target file and its schema receipt back after each
transaction, verifies the final build, and restores the file's original TODO
skeleton if that transaction fails. The legacy transport remains available with
`--agent-transport exec`.

## Setup

Requirements:

- Conda
- JDK 11 with `java`, `javac`, and `jdeps`
- Maven 3.8 or newer
- Node.js/npm
- Cangjie SDK 1.0.5 with `cjc` and `cjpm`

Create the Python environment and initialize the Cangjie SDK:

```bash
conda env create -f environment.yaml
conda activate x2cangjie
source /path/to/cangjie/envsetup.sh
```

Install and authenticate Codex:

```bash
npm install -g @openai/codex
codex login
codex login status
```

API-key authentication is also supported:

```bash
export OPENAI_API_KEY="sk-..."
printenv OPENAI_API_KEY | codex login --with-api-key
```

Optional model defaults belong in `~/.codex/config.toml`:

```toml
model_provider = "openai"
model = "<model available to your account>"
```

Do not commit API keys, `.env` files, or `~/.codex/auth.json`.

## Run

The projects under `projects/cleaned_final_projects_evosuite_cleaned_base` are
already preprocessed and can be used directly:

```bash
PROJECT=commons-cli
SCHEMA_MODEL=codex-baseline
SUFFIX=_evosuite_cleaned_base
TEMPERATURE=0.0
PROJECT_ROOT=projects/cleaned_final_projects_evosuite_cleaned_base

bash scripts/java/create_schema.sh \
  "$PROJECT" "$SCHEMA_MODEL" "$TEMPERATURE" "$SUFFIX" "$PROJECT_ROOT"

bash scripts/java/get_dependencies.sh \
  "$PROJECT" "$SUFFIX" "$PROJECT_ROOT"

bash scripts/java/create_skeleton.sh \
  "$PROJECT" "$SCHEMA_MODEL" "$SUFFIX" "$TEMPERATURE" false

bash scripts/java/translate_fragment.sh \
  "$PROJECT" "$SCHEMA_MODEL" "$SUFFIX" "$TEMPERATURE" false
```

`SCHEMA_MODEL` is the schema output namespace, not the Codex model name. The
skeleton and fragment commands use the model in `~/.codex/config.toml` by
default; pass a sixth argument to either command to override it.
