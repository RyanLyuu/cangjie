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

## Codex Configuration

The baseline launches the local Codex CLI. Credentials are never read from the
repository: every user must authenticate Codex on their own machine.

Install Codex and sign in with a personal ChatGPT account:

```bash
npm install -g @openai/codex
codex login
codex login status
```

Alternatively, authenticate with a personal OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
printenv OPENAI_API_KEY | codex login --with-api-key
codex login status
```

PowerShell users can run:

```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_API_KEY | codex login --with-api-key
```

Personal Codex defaults belong in `~/.codex/config.toml`:

```toml
model_provider = "openai"
model = "<a Codex model available to your account>"
```

Do not commit API keys, `.env` files, or `~/.codex/auth.json`. The example
`configs/model_configs.yaml.example` is not used to authenticate the Codex
baseline. See the official [Codex authentication](https://developers.openai.com/codex/auth)
and [configuration](https://developers.openai.com/codex/config-basic) guides.

## Quick Start

```bash
conda env create -f environment.yaml
conda activate x2cangjie

# The projects/cleaned_final_projects_evosuite_cleaned_base tree is already
# preprocessed and can be used directly.
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

`schema_model` (for example, `codex-baseline`) is only the namespace used below
`data/java/schemas...`; it does not select the Agent model. If the optional
`agent_model` argument is omitted, Codex uses `~/.codex/config.toml`.

The checked-in cleaned projects do not need preprocessing again. Regenerating
them with the preprocessing scripts requires Maven, suitable JDK versions, the
Java Tree-sitter grammar, and the `java-callgraph` fat JAR.

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
projects/cleaned_final_projects_evosuite_cleaned_base/  Ready-to-use inputs
projects/original_projects/                             Original source snapshots
data/java/                Call graphs, schemas, and dependency artifacts
```
