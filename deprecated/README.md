# Deprecated Archive

This directory preserves the retired type-resolution implementation and
historical x2cangjie artifacts. Active code must not import or invoke it.

## Contents

```text
legacy_pipeline/
  generics_rule_lib/    Previous generic conversion rule library
  scripts/java/         Retired type-resolution and type-corpus entry points
  src/java/             Retired type-resolution, generic, and crawler modules
  debug.sh              Previous end-to-end debug entry point
non_baseline/
  src/java/             RAG, mock validation, analysis, and retired translators
  scripts/java/         Retired entry points for those modules
  tests/                Tests coupled to the retired implementations
  configs/              Previous OpenAI/RAG/prompt configuration
  docs/                 Documentation for superseded workflows
  root/                 Retired root-level helpers and generic rule data
data/java/
  analysis/             Translation and type-analysis snapshots
  skeletons/            Generated Cangjie skeletons and translations
  type_resolution/      Previous type maps and project decisions
reports/
  docs/                 Historical workflow, build-error, log, and experiment reports
  root/                 Reports formerly stored at repository root
  artifacts/            Generated report artifacts
misc/merge-files/       Preserved merge-tool temporary files
```

## Status

- The legacy type resolver is retained for provenance and comparison with the
  new Agent/Skill implementation.
- Internal imports and shell paths still reflect the former repository layout;
  archived commands are not guaranteed to execute from this location.
- Current Type Resolution Skill designs are not deprecated. They live in
  `docs/design/`, and the self-contained development Skill lives in
  `resolve-cangjie-types/`.
- Active code is limited to preprocessing/schema generation and the current
  type-resolution, skeleton-MCP, and file-level baseline workflow.

Do not import code from either archive into the active runtime. Port only
validated behavior into the baseline or the self-contained development Skill.
