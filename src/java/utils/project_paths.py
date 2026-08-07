from __future__ import annotations

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
