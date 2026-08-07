from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.java.type_resolution.agent import CodexRunner
from src.java.type_resolution.schema import load_schema
from src.java.translation.cangjie_compilation_validation import (
    _insert_import,
    extract_method_body,
    find_fragment_in_skeleton,
    replace_fragment_in_skeleton,
)
from src.java.translation.dependency_order import fragment_order, schema_scc_batches


FRAGMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "translation": {"type": "string"},
        "imports": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["translation", "imports", "reasoning"],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate Java fragments with Codex and incremental cjpm build feedback"
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--model", required=True, help="Schema namespace")
    parser.add_argument("--temperature", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--agent-model", default="")
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--cjpm-executable", default="cjpm")
    parser.add_argument("--agent-timeout", type=int, default=1800)
    parser.add_argument("--compile-timeout", type=int, default=300)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-dir", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path.cwd().resolve()
    schema_dir = Path(
        f"data/java/schemas{args.suffix}/{args.model}/{args.temperature}/{args.project}"
    )
    translation_root = Path(
        f"data/java/skeletons/translations/{args.model}/{args.temperature}/{args.project}"
    )
    if not schema_dir.is_dir():
        raise SystemExit(f"schema directory not found: {schema_dir}")
    if not (translation_root / "cjpm.toml").is_file():
        raise SystemExit("translation skeleton is missing; run create_skeleton.sh first")

    runner = CodexRunner(
        executable=args.codex_executable,
        model=args.agent_model,
        timeout=args.agent_timeout,
    )
    batches = schema_scc_batches(
        schema_dir,
        project=args.project,
        suffix=args.suffix,
        include_tests=args.include_tests,
    )
    paths = [path for batch in batches for path in batch]
    if not args.resume:
        _reset_translation_skeletons(paths)
    initial_build = _build(translation_root, args.cjpm_executable, args.compile_timeout)
    if initial_build[0] != 0:
        raise SystemExit("translation TODO skeleton does not compile:\n" + initial_build[1])

    summary = {
        "project": args.project, "files": [],
        "completed": 0, "failed": 0, "skipped": 0,
    }
    for batch_index, batch in enumerate(batches):
        for path in batch:
            result = _translate_file(
                path,
                schema_dir,
                translation_root,
                runner,
                args,
                workspace,
                batch_index,
            )
            summary["files"].append(result)
            summary["completed"] += result["completed"]
            summary["failed"] += result["failed"]
            summary["skipped"] += result["skipped"]

    output = Path(args.output_dir) if args.output_dir else Path(
        f"data/java/fragment_runs/{args.project}/{args.model}/{args.temperature}{args.suffix}"
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _translate_file(path, schema_dir, translation_root, runner, args, workspace, batch_index):
    schema = load_schema(path)
    fragments = fragment_order(schema)
    session_id = ""
    completed = 0
    failed = 0
    skipped = 0
    for fragment_index, fragment in enumerate(fragments):
        fragment.update({
            "schema_name": path.stem,
            "cangjie_skeleton_path": schema.get("cangjie_skeleton_path", ""),
            "cangjie_translations_skeleton_path": schema.get(
                "cangjie_translations_skeleton_path", ""
            ),
        })
        source_info = _fragment_info(schema, fragment)
        skeleton_path = Path(fragment["cangjie_translations_skeleton_path"])
        skeleton_content = skeleton_path.read_text(encoding="utf-8") if skeleton_path.is_file() else ""
        signature, _, _ = find_fragment_in_skeleton(
            skeleton_content, fragment, str(schema_dir)
        )
        if signature is None:
            if source_info.get("translation_status") != "completed":
                source_info["translation_status"] = "skipped-no-todo-fragment"
            path.write_text(json.dumps(schema, indent=4, ensure_ascii=False), encoding="utf-8")
            skipped += 1
            continue
        feedback = []
        accepted = None
        for attempt in range(1, args.max_attempts + 1):
            prompt = _fragment_prompt(
                schema,
                fragment,
                source_info,
                feedback,
                include_schema=not session_id,
            )
            agent_result = runner.run(
                prompt,
                FRAGMENT_SCHEMA,
                workspace=workspace,
                session_id=session_id,
            )
            if agent_result.session_id:
                session_id = agent_result.session_id
            if agent_result.status != "success" or agent_result.content is None:
                feedback.append(agent_result.stderr or "Codex did not return a structured result")
                continue
            candidate = str(agent_result.content.get("translation", "")).strip()
            imports = [str(item).strip() for item in agent_result.content.get("imports", [])]
            success, diagnostic = _compile_candidate(
                candidate,
                imports,
                fragment,
                schema_dir,
                translation_root,
                args.cjpm_executable,
                args.compile_timeout,
            )
            if success:
                accepted = {
                    "translation": candidate,
                    "imports": imports,
                    "reasoning": str(agent_result.content.get("reasoning", "")),
                    "attempts": attempt,
                }
                break
            feedback.append(diagnostic)

        if accepted:
            source_info["translation"] = accepted["translation"]
            source_info["translation_imports"] = accepted["imports"]
            source_info["translation_reasoning"] = accepted["reasoning"]
            source_info["translation_status"] = "completed"
            source_info["cangjie_compilation"] = {
                "outcome": "success", "attempts": accepted["attempts"]
            }
            completed += 1
        else:
            source_info["translation_status"] = "failed-todo-retained"
            source_info["cangjie_compilation"] = {
                "outcome": "failed", "attempts": args.max_attempts,
                "feedback": feedback,
            }
            failed += 1
        source_info["generation_timestamp"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(schema, indent=4, ensure_ascii=False), encoding="utf-8")

    return {
        "schema_file": path.name,
        "scc_batch": batch_index,
        "fragments": len(fragments),
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "session_id": session_id,
    }


def _fragment_info(schema: dict, fragment: dict) -> dict:
    class_info = schema["classes"][fragment["class_key"]]
    kind = fragment["fragment_type"]
    if kind == "field":
        return class_info["fields"][fragment["fragment_name"]]
    if kind == "static_initializer":
        return class_info["static_initializers"][fragment["fragment_name"]]
    return class_info["methods"][fragment["fragment_name"]]


def _fragment_prompt(schema, fragment, source_info, feedback, *, include_schema):
    task = (
        "Translate exactly this Java fragment into Cangjie for the existing TODO skeleton. "
        "Use the signatures and materialized types already present in the skeleton. Return a full "
        "field assignment for a field, or a complete callable declaration for a method, constructor, "
        "or static initializer. Do not translate other fragments. Do not add tests or mock behavior."
    )
    parts = [task]
    if include_schema:
        parts.append("FILE SCHEMA:\n" + json.dumps(schema, indent=2, ensure_ascii=False))
        skeleton_path = Path(str(schema.get("cangjie_translations_skeleton_path", "")))
        if skeleton_path.is_file():
            parts.append("CURRENT CANGJIE SKELETON:\n" + skeleton_path.read_text(encoding="utf-8"))
    parts.append("FRAGMENT METADATA:\n" + json.dumps(fragment, indent=2, ensure_ascii=False))
    parts.append("JAVA FRAGMENT:\n" + "\n".join(source_info.get("body", [])))
    if feedback:
        parts.append("CJPM BUILD FEEDBACK:\n" + "\n\n".join(feedback))
    return "\n\n".join(parts)


def _compile_candidate(
    candidate, imports, fragment, schema_dir, translation_root, executable, timeout
):
    skeleton_path = Path(fragment["cangjie_translations_skeleton_path"])
    if not skeleton_path.is_file():
        return False, f"translation skeleton not found: {skeleton_path}"
    original = skeleton_path.read_text(encoding="utf-8")
    signature, _, _ = find_fragment_in_skeleton(original, fragment, str(schema_dir))
    if signature is None:
        return False, "fragment signature was not found in the current skeleton"
    body = extract_method_body(candidate, fragment, str(schema_dir))
    modified = replace_fragment_in_skeleton(
        original, signature, body, fragment["fragment_type"]
    )
    for item in imports:
        for line in item.splitlines():
            line = line.strip()
            if not line:
                continue
            if not line.startswith("import "):
                return False, f"invalid Cangjie import: {line}"
            modified = _insert_import(modified, line)
    if modified == original:
        return False, "candidate did not replace the TODO fragment"
    skeleton_path.write_text(modified, encoding="utf-8")
    returncode, diagnostic = _build(translation_root, executable, timeout)
    if returncode != 0:
        skeleton_path.write_text(original, encoding="utf-8")
        return False, diagnostic
    return True, diagnostic


def _build(root: Path, executable: str, timeout: int) -> tuple[int, str]:
    command = shutil.which(executable) or (executable if Path(executable).is_file() else "")
    if not command:
        return 127, f"Cangjie package manager not found: {executable}"
    try:
        result = subprocess.run(
            [command, "build"], capture_output=True, text=True, timeout=timeout,
            cwd=root, check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"cjpm build timed out after {timeout}s"
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode, output


def _reset_translation_skeletons(paths):
    for path in paths:
        schema = load_schema(path)
        source = Path(str(schema.get("cangjie_skeleton_path", "")))
        target = Path(str(schema.get("cangjie_translations_skeleton_path", "")))
        if not source.is_file() or not target.parent.exists():
            raise SystemExit(f"skeleton paths are incomplete in {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


if __name__ == "__main__":
    raise SystemExit(main())
