from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_java_project_root(
    project: str, suffix: str = "", configured_root: str = ""
) -> Path:
    """Resolve a preprocessed Java project while retaining the old layout fallback."""
    candidates = []
    if configured_root:
        root = Path(configured_root)
        candidates.append(root / project if root.name != project else root)
    candidates.extend([
        REPO_ROOT / f"projects/cleaned_final_projects{suffix}" / project,
        REPO_ROOT / f"projects/java/cleaned_final_projects{suffix}" / project,
    ])
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    tried = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"preprocessed Java project not found; tried: {tried}")


def materialize_call_graph(
    project_dir: str | Path,
    project_name: str,
    data_root: str | Path | None = None,
) -> Path:
    """Copy the checked-in project call graph to the generated-data layout if needed."""
    project_dir = Path(project_dir)
    root = Path(data_root) if data_root else REPO_ROOT / "data/java/call_graphs"
    target = root / project_name / "callgraph.txt"
    if target.is_file():
        return target

    source = project_dir / "callgraph.txt"
    if not source.is_file():
        raise FileNotFoundError(
            f"call graph not found; expected {target} or {source}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target
