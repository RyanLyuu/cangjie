# Codex Baseline

## Prerequisites

- Run from the repository root with `PYTHONPATH` pointing to it.
- Authenticate the local `codex` CLI.
- Put `cjc` and `cjpm` on `PATH`.
- Generate Java schemas and dependency artifacts first.

For the checked-in cleaned projects, generate those artifacts directly with:

```bash
bash scripts/java/create_schema.sh \
  commons-cli codex-baseline 0.0 _evosuite_cleaned_base \
  projects/cleaned_final_projects_evosuite_cleaned_base

bash scripts/java/get_dependencies.sh \
  commons-cli _evosuite_cleaned_base \
  projects/cleaned_final_projects_evosuite_cleaned_base
```

`schema_model` is only the schema output namespace; it does not select the
Codex model. The optional `agent_model` argument on the commands below selects
the actual Codex model. If omitted, Codex uses its local configuration.

## Skeleton Command

```bash
bash scripts/java/create_skeleton.sh \
  <project> <schema_model> <suffix> <temperature> [include_tests] [agent_model]
```

This command:

1. sends one complete file Schema and all of its type occurrences to one Codex session;
2. compiles every proposed type/import in an isolated `cjc` probe;
3. retries failed occurrences in the same session, at most three times;
4. falls back to `Any`, an unbounded type parameter, or a generated interface;
5. writes direct `translated_target_type` and `imports` fields into `type_translations`;
6. starts a dedicated skeleton-stage Codex agent, which calls the local
   `generate_cangjie_skeleton` MCP tool;
7. the tool generates both TODO skeleton trees and requires `cjpm build` to
   succeed. Its receipt is written under `data/java/skeleton_generation_runs/`.

Run only the type stage with:

```bash
bash scripts/java/resolve_types.sh \
  <project> <schema_model> <temperature> <suffix> [include_tests] [agent_model]
```

Type run records are written below
`data/java/type_resolution_runs/<project>/<schema_model>/<temperature+suffix>/`.

## Fragment Command

```bash
bash scripts/java/translate_fragment.sh \
  <project> <schema_model> <suffix> <temperature> [include_tests] [agent_model] [agent_transport] [max_builds]
```

The command orders files with fully qualified `schema_name::class_key` nodes and
keeps cycles as SCC batches. By default it starts one long-lived Codex
`app-server` process and sends one turn per Java file on the same thread. This
avoids restarting `codex exec` for every file while preserving the same shared
context. Use `--agent-transport exec` for the legacy one-shot `exec/resume`
transport. In either mode it assigns one Java file at a time to that shared
agent. Before the first turn, the controller creates an isolated temporary
workspace containing only the current Java project, its schema directory, its
base/translation skeletons, and project-local dependency metadata. Codex runs
with the `workspace-write` sandbox from that directory; paths outside the
temporary project workspace are not part of the agent's execution scope. The
agent edits only the matching translation skeleton file and owns the
edit/`cjpm build`/repair loop. The agent may invoke `cjpm build` at most three
times per file by default; a temporary wrapper counts those attempts and rejects
the fourth one. The 300-second file limit remains an emergency watchdog for a
stuck agent or compiler (280 seconds for the agent and up to 20 seconds for the
controller's final build), rather than the normal completion criterion. At the
file boundary the controller verifies that every TODO in the target file was
replaced, that no protected source/config/schema path changed, and that its
final `cjpm build` succeeds. This controller build is separate from the agent's
three-attempt budget. Only the successful target file and its schema receipt are
synchronized back to the real project tree.
Any timeout, failed build, or out-of-scope edit restores the original TODO
skeleton and schema state for that file.

This baseline command does not use RAG, progressive KB, pseudocode, grammar
injection, syntax retrieval, mock tests, or runtime tests.
