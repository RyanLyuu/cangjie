import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.java.translation.baseline_fragment_translation import (
    _AgentBuildBudget,
    _agent_environment,
    _has_skeleton_todo,
    _isolated_project_workspace,
    _sync_file_transaction,
    _source_path_for,
    _translate_file_transaction,
    _validate_timeouts,
    build_parser,
)
from src.java.translation.dependency_order import _dependency_first_sccs, fragment_order
from src.java.type_resolution.agent import AgentResult, AgentRunner


class BaselineDependencyOrderTest(unittest.TestCase):
    def test_sccs_are_kept_as_batches_and_dependencies_run_first(self):
        graph = {
            "a": {"b"},
            "b": {"a"},
            "c": {"a"},
            "d": set(),
        }
        batches = _dependency_first_sccs(graph)
        self.assertIn(["a", "b"], batches)
        self.assertLess(batches.index(["a", "b"]), batches.index(["c"]))

    def test_fragment_order_respects_field_and_method_dependencies(self):
        schema = {
            "classes": {
                "1-20:Demo": {
                    "start": 1,
                    "extends": [],
                    "implements": [],
                    "fields": {
                        "2-2:base": {"start": 2, "body": ["int base = 1;"]},
                        "3-3:derived": {"start": 3, "body": ["int derived = base + 1;"]},
                    },
                    "methods": {
                        "10-12:caller": {
                            "start": 10,
                            "is_constructor": False,
                            "calls": [["project", "Demo", "callee()"]],
                        },
                        "7-9:callee": {
                            "start": 7,
                            "is_constructor": False,
                            "calls": [],
                        },
                        "4-6:Demo": {
                            "start": 4,
                            "is_constructor": True,
                            "calls": [],
                        },
                    },
                }
            }
        }
        order = fragment_order(schema)
        names = [item["fragment_name"] for item in order]
        self.assertLess(names.index("2-2:base"), names.index("3-3:derived"))
        self.assertLess(names.index("4-6:Demo"), names.index("7-9:callee"))
        self.assertLess(names.index("7-9:callee"), names.index("10-12:caller"))


class _FileEditingRunner(AgentRunner):
    def __init__(self, edit):
        self.edit = edit
        self.calls = []

    def run(self, prompt, output_schema, *, workspace, session_id=""):
        self.calls.append((prompt, output_schema, Path(workspace), session_id))
        self.edit()
        return AgentResult(
            "success", {"status": "success", "summary": "target updated"},
            session_id="shared-codex-session",
        )


class FileTransactionTest(unittest.TestCase):
    def test_file_translation_defaults_to_a_300_second_transaction(self):
        args = build_parser().parse_args([
            "--project", "demo", "--model", "codex", "--temperature", "0.0",
        ])
        self.assertEqual(args.file_timeout, 300)
        self.assertEqual(args.final_build_timeout, 20)
        self.assertEqual(args.max_builds, 3)
        self.assertEqual(args.agent_transport, "app-server")

    def test_agent_build_budget_rejects_the_fourth_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_cjpm = root / "real-cjpm"
            real_cjpm.write_text(
                "#!/bin/sh\nprintf x >> calls\nexit 0\n", encoding="utf-8"
            )
            real_cjpm.chmod(0o755)
            budget = _AgentBuildBudget.create(root, str(real_cjpm), 3)
            try:
                environment = _agent_environment(os.environ.copy(), budget)
                results = [
                    subprocess.run(
                        [str(budget.wrapper_path), "build"],
                        cwd=root,
                        env=environment,
                        check=False,
                    )
                    for _ in range(4)
                ]
                self.assertEqual(
                    [result.returncode for result in results], [0, 0, 0, 125]
                )
                self.assertEqual(budget.count(), 3)
                self.assertTrue(budget.exceeded())
            finally:
                budget.cleanup()

    def test_agent_build_budget_has_a_hard_upper_bound_of_three(self):
        args = build_parser().parse_args([
            "--project", "demo", "--model", "codex", "--temperature", "0.0",
            "--max-builds", "4",
        ])
        with self.assertRaises(SystemExit):
            _validate_timeouts(args)

    def test_file_translation_rejects_timeout_over_300_seconds(self):
        args = build_parser().parse_args([
            "--project", "demo", "--model", "codex", "--temperature", "0.0",
            "--file-timeout", "301",
        ])
        with self.assertRaises(SystemExit):
            _validate_timeouts(args)

    def test_todo_detection_ignores_non_skeleton_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Demo.cj"
            path.write_text("// TODO someday improve this\n", encoding="utf-8")
            self.assertFalse(_has_skeleton_todo(path))
            path.write_text("func demo() { throw Exception('TODO') }\n", encoding="utf-8")
            self.assertTrue(_has_skeleton_todo(path))

    def _fixture(self, root: Path, *, build_exit: int = 0):
        workspace = root / "workspace"
        schema_dir = workspace / "schemas"
        translation_root = workspace / "translation"
        source = workspace / "projects" / "Demo.java"
        target = translation_root / "src" / "Demo.cj"
        peer = translation_root / "src" / "Peer.cj"
        schema_dir.mkdir(parents=True)
        source.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        source.write_text("class Demo {}\n", encoding="utf-8")
        target.write_text("class Demo {\n  func value() { throw Exception('TODO') }\n}\n", encoding="utf-8")
        peer.write_text("class Peer {}\n", encoding="utf-8")
        (translation_root / "cjpm.toml").write_text("[package]\nname = 'demo'\n", encoding="utf-8")
        cjpm = workspace / "cjpm"
        cjpm.write_text(f"#!/bin/sh\nexit {build_exit}\n", encoding="utf-8")
        cjpm.chmod(0o755)
        schema_path = schema_dir / "demo.json"
        schema_path.write_text(json.dumps({
            "path": str(source),
            "cangjie_translations_skeleton_path": str(target),
            "classes": {"1-3:Demo": {
                "start": 1,
                "extends": [], "implements": [], "static_initializers": {},
                "fields": {},
                "methods": {"2-2:value": {
                    "start": 2, "is_constructor": False, "calls": [],
                    "translation_status": "pending", "cangjie_compilation": "pending",
                }},
            }},
        }), encoding="utf-8")
        args = SimpleNamespace(
            file_timeout=120,
            final_build_timeout=20,
            cjpm_executable=str(cjpm),
        )
        return workspace, schema_dir, translation_root, schema_path, target, peer, args

    def test_file_agent_commits_target_after_the_final_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, schema_dir, translation_root, schema, target, _, args = self._fixture(root)
            runner = _FileEditingRunner(
                lambda: target.write_text("class Demo { func value() { return } }\n", encoding="utf-8")
            )

            result = _translate_file_transaction(
                schema, schema_dir, translation_root, runner, args, workspace, 0,
                session_id="prior-session",
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["session_id"], "shared-codex-session")
            self.assertEqual(runner.calls[0][3], "prior-session")
            self.assertNotIn("throw Exception('TODO')", target.read_text())
            stored = json.loads(schema.read_text(encoding="utf-8"))
            self.assertEqual(stored["file_translation"]["status"], "success")
            self.assertEqual(
                stored["classes"]["1-3:Demo"]["methods"]["2-2:value"]["translation_status"],
                "completed",
            )

    def test_failed_final_build_restores_the_original_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, schema_dir, translation_root, schema, target, _, args = self._fixture(root, build_exit=1)
            original = target.read_text(encoding="utf-8")
            runner = _FileEditingRunner(
                lambda: target.write_text("class Demo { func value() { return } }\n", encoding="utf-8")
            )

            result = _translate_file_transaction(
                schema, schema_dir, translation_root, runner, args, workspace, 0,
                session_id="",
            )

            self.assertEqual(result["status"], "build_failed")
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            stored = json.loads(schema.read_text(encoding="utf-8"))
            self.assertEqual(stored["file_translation"]["status"], "build_failed")
            self.assertEqual(
                stored["classes"]["1-3:Demo"]["methods"]["2-2:value"]["translation_status"],
                "pending",
            )

    def test_changes_outside_the_target_are_reverted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace, schema_dir, translation_root, schema, target, peer, args = self._fixture(root)
            original_target = target.read_text(encoding="utf-8")
            original_peer = peer.read_text(encoding="utf-8")

            def edit():
                target.write_text("class Demo { func value() { return } }\n", encoding="utf-8")
                peer.write_text("class Peer { func changed() {} }\n", encoding="utf-8")

            result = _translate_file_transaction(
                schema, schema_dir, translation_root, _FileEditingRunner(edit), args,
                workspace, 0, session_id="",
            )

            self.assertEqual(result["status"], "out_of_scope_changes")
            self.assertEqual(target.read_text(encoding="utf-8"), original_target)
            self.assertEqual(peer.read_text(encoding="utf-8"), original_peer)

    def test_isolated_workspace_contains_only_current_project_and_syncs_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            project_root = workspace / "projects" / "cleaned" / "demo"
            sibling_root = workspace / "projects" / "cleaned" / "other"
            source = project_root / "src" / "main" / "java" / "Demo.java"
            sibling = sibling_root / "src" / "main" / "java" / "Other.java"
            schema_dir = workspace / "data" / "java" / "schemas" / "codex" / "0.0" / "demo"
            translation_root = workspace / "data" / "java" / "skeletons" / "translations" / "codex" / "0.0" / "demo"
            target = translation_root / "src" / "Demo.cj"
            source.parent.mkdir(parents=True)
            sibling.parent.mkdir(parents=True)
            schema_dir.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.write_text("class Demo {}\n", encoding="utf-8")
            sibling.write_text("class Other {}\n", encoding="utf-8")
            target.write_text(
                "class Demo {\n  func value() { throw Exception('TODO') }\n}\n",
                encoding="utf-8",
            )
            (translation_root / "cjpm.toml").write_text(
                "[package]\nname = 'demo'\n", encoding="utf-8"
            )
            cjpm = workspace / "cjpm"
            cjpm.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            cjpm.chmod(0o755)
            schema_path = schema_dir / "demo.json"
            schema_path.write_text(json.dumps({
                "path": "projects/cleaned/demo/src/main/java/Demo.java",
                "cangjie_translations_skeleton_path": "data/java/skeletons/translations/codex/0.0/demo/src/Demo.cj",
                "classes": {"1-3:Demo": {
                    "start": 1,
                    "extends": [], "implements": [], "static_initializers": {},
                    "fields": {},
                    "methods": {"2-2:value": {
                        "start": 2, "is_constructor": False, "calls": [],
                        "translation_status": "pending", "cangjie_compilation": "pending",
                    }},
                }},
            }), encoding="utf-8")

            with _isolated_project_workspace(
                workspace, "demo", [schema_path], schema_dir, translation_root,
            ) as isolated:
                isolated_schema = isolated.map_path(schema_path)
                isolated_translation = isolated.map_path(translation_root)
                self.assertTrue(isolated.map_path(source).is_file())
                self.assertFalse(isolated.map_path(sibling).exists())

                def edit_isolated_target():
                    isolated.map_path(target).write_text(
                        "class Demo { func value() { return } }\n", encoding="utf-8"
                    )

                runner = _FileEditingRunner(edit_isolated_target)
                args = SimpleNamespace(
                    file_timeout=120,
                    final_build_timeout=20,
                    cjpm_executable=str(cjpm),
                )
                result = _translate_file_transaction(
                    isolated_schema,
                    isolated.map_path(schema_dir),
                    isolated_translation,
                    runner,
                    args,
                    isolated.root,
                    0,
                    session_id="",
                )
                self.assertEqual(result["status"], "success")
                _sync_file_transaction(isolated, isolated_schema, result)

            self.assertIn("return", target.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(schema_path.read_text(encoding="utf-8"))["file_translation"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
