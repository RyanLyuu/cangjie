import json
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path

from src.java.type_resolution.agent import AgentResult, AgentRunner, CodexRunner
from src.java.type_resolution.models import ProbeResult
from src.java.type_resolution.resolver import TYPE_DECISIONS_SCHEMA, TypeResolutionService
from src.java.type_resolution.schema import get_materialized_type, load_occurrences


def sample_schema() -> dict:
    occurrences = [
        {
            "occurrence_id": "occ-string-1",
            "class_key": "1-8:Demo",
            "fragment_kind": "field",
            "fragment_key": "2-2:name",
            "variation": "types",
            "identifier": "String",
            "source_type": "String",
            "role": "field",
            "start_line": 2,
            "start_column": 5,
            "end_line": 2,
            "end_column": 11,
            "context_before": ["class Demo {"],
            "source_line": "    String name;",
            "context_after": [],
        },
        {
            "occurrence_id": "occ-demo-1",
            "class_key": "1-8:Demo",
            "fragment_kind": "method",
            "fragment_key": "4-6:copy",
            "variation": "return_types",
            "identifier": "Demo",
            "source_type": "Demo",
            "role": "return",
            "start_line": 4,
            "start_column": 5,
            "end_line": 4,
            "end_column": 9,
            "context_before": [],
            "source_line": "    Demo copy() {",
            "context_after": [],
        },
    ]
    return {
        "path": "projects/demo/src/main/java/example/Demo.java",
        "imports": {},
        "import_map": {},
        "type_occurrences": occurrences,
        "classes": {
            "1-8:Demo": {
                "start": 1,
                "end": 8,
                "body": ["class Demo {}"],
                "modifiers": [],
                "type_parameters": [],
                "extends": [],
                "implements": [],
                "type_translations": {},
                "fields": {
                    "2-2:name": {
                        "start": 2,
                        "end": 2,
                        "body": ["String name;"],
                        "modifiers": [],
                        "types": ["String"],
                        "type_translations": {"types": {}},
                    }
                },
                "methods": {
                    "4-6:copy": {
                        "start": 4,
                        "end": 6,
                        "body": ["Demo copy() {", "return this;", "}"],
                        "annotations": [],
                        "modifiers": [],
                        "type_parameters": [],
                        "return_types": ["Demo"],
                        "body_types": [],
                        "parameters": [],
                        "type_translations": {"return_types": {}},
                    }
                },
            }
        },
    }


class FakeRunner(AgentRunner):
    def __init__(self, responses):
        self.responses = list(responses)
        self.sessions = []

    def run(self, prompt, output_schema, *, workspace, session_id=""):
        self.sessions.append(session_id)
        response = self.responses.pop(0)
        if response is None:
            return AgentResult("error", None, session_id or "session-1", stderr="agent error", returncode=1)
        return AgentResult("success", response, session_id or "session-1")


class FakeProbe:
    def ensure_available(self):
        return None

    def probe(self, occurrence, decision, *, project_types, placeholder_names=()):
        if decision.translated_target_type == "BadType":
            return ProbeResult(False, "unknown type BadType")
        return ProbeResult(True, "")


class RecordingProbe(FakeProbe):
    def __init__(self):
        self.calls = []

    def probe(self, occurrence, decision, *, project_types, placeholder_names=()):
        self.calls.append((decision, placeholder_names))
        return super().probe(
            occurrence,
            decision,
            project_types=project_types,
            placeholder_names=placeholder_names,
        )


class BaselineTypeResolutionTest(unittest.TestCase):
    def write_schema(self, root: Path) -> Path:
        path = root / "demo.src.main.example.Demo.json"
        path.write_text(json.dumps(sample_schema()), encoding="utf-8")
        return path

    def test_probe_failure_retries_in_same_file_session_and_preserves_project_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp) / "schemas"
            schema_dir.mkdir()
            path = self.write_schema(schema_dir)
            runner = FakeRunner([
                {"decisions": [
                    {"occurrence_id": "occ-string-1", "translated_target_type": "BadType", "imports": [], "reasoning": "first"},
                    {"occurrence_id": "occ-demo-1", "translated_target_type": "Wrong", "imports": [], "reasoning": "wrong"},
                ]},
                {"decisions": [
                    {"occurrence_id": "occ-string-1", "translated_target_type": "String", "imports": [], "reasoning": "fixed"},
                ]},
            ])
            service = TypeResolutionService(
                runner, FakeProbe(), Path(tmp), "demo", max_attempts=3
            )
            summary = service.resolve_project(schema_dir)

            self.assertEqual(summary["fallback"], 0)
            self.assertEqual(runner.sessions, ["", "session-1"])
            data = json.loads(path.read_text())
            field = data["classes"]["1-8:Demo"]["fields"]["2-2:name"]
            method = data["classes"]["1-8:Demo"]["methods"]["4-6:copy"]
            self.assertEqual(get_materialized_type(field, "types", "String"), "String")
            self.assertEqual(get_materialized_type(method, "return_types", "Demo"), "Demo")
            self.assertEqual(field["type_translations"]["types"]["String"]["attempts"], 2)

    def test_three_agent_failures_use_value_and_structural_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp) / "schemas"
            schema_dir.mkdir()
            data = sample_schema()
            structural = {
                "occurrence_id": "occ-parent-1",
                "class_key": "1-8:Demo",
                "fragment_kind": "class",
                "fragment_key": "1-8:Demo",
                "variation": "extends",
                "identifier": "0|MissingParent",
                "source_type": "MissingParent",
                "role": "extends",
                "start_line": 1,
                "start_column": 20,
                "end_line": 1,
                "end_column": 33,
            }
            data["type_occurrences"].append(structural)
            cls = data["classes"]["1-8:Demo"]
            cls["extends"] = ["MissingParent"]
            cls["type_translations"]["extends"] = {}
            path = schema_dir / "demo.src.main.example.Demo.json"
            path.write_text(json.dumps(data), encoding="utf-8")

            service = TypeResolutionService(
                FakeRunner([None, None, None]), FakeProbe(), Path(tmp), "demo", max_attempts=3
            )
            summary = service.resolve_project(schema_dir)
            self.assertEqual(summary["fallback"], 2)
            materialized = json.loads(path.read_text())
            field = materialized["classes"]["1-8:Demo"]["fields"]["2-2:name"]
            self.assertEqual(get_materialized_type(field, "types", "String"), "Any")
            placeholders = materialized["generated_type_placeholders"]
            self.assertEqual(len(placeholders), 1)
            self.assertTrue(placeholders[0]["name"].startswith("X2CangjieType_"))

    def test_structural_fallback_probe_uses_local_placeholder_without_project_import(self):
        occurrence_data = {
            "occurrence_id": "occ-parent-1",
            "class_key": "1-8:Demo",
            "fragment_kind": "class",
            "fragment_key": "1-8:Demo",
            "variation": "extends",
            "identifier": "0|MissingParent",
            "source_type": "MissingParent",
            "role": "extends",
            "start_line": 1,
            "start_column": 20,
            "end_line": 1,
            "end_column": 33,
        }
        data = sample_schema()
        data["type_occurrences"] = [occurrence_data]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            _, occurrences = load_occurrences(path)
            probe = RecordingProbe()
            service = TypeResolutionService(
                FakeRunner([]), probe, Path(tmp), "demo", max_attempts=1
            )
            resolution = service._fallback(occurrences[0])

        probe_decision, placeholders = probe.calls[-1]
        self.assertEqual(probe_decision.imports, ())
        self.assertEqual(placeholders, (resolution.decision.translated_target_type,))
        self.assertEqual(resolution.decision.imports, ("import demo.X2CangjieType_parent_1",))

    def test_occurrence_rows_keep_duplicate_source_types_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.json"
            data = sample_schema()
            duplicate = dict(data["type_occurrences"][0])
            duplicate["occurrence_id"] = "occ-string-2"
            duplicate["start_line"] = 7
            data["type_occurrences"].append(duplicate)
            path.write_text(json.dumps(data), encoding="utf-8")
            _, occurrences = load_occurrences(path)
            string_ids = [item.occurrence_id for item in occurrences if item.source_type == "String"]
            self.assertEqual(string_ids, ["occ-string-1", "occ-string-2"])

    def test_schema_generation_locates_repeated_body_type_occurrences(self):
        tqdm = types.ModuleType("tqdm")
        tqdm.tqdm = lambda *args, **kwargs: None
        tree_sitter = types.ModuleType("tree_sitter")
        tree_sitter.Language = object
        tree_sitter.Parser = object
        sys.modules.setdefault("tqdm", tqdm)
        sys.modules.setdefault("tree_sitter", tree_sitter)
        module = importlib.import_module("src.java.decomposition.create_schema")
        code = (
            "class Demo {\n"
            "  String run(String value) {\n"
            "    Map<String, String> first;\n"
            "    Map<String, String> second;\n"
            "  }\n"
            "}\n"
        )
        method = {
            "start": 2,
            "end": 5,
            "body": code.splitlines()[1:5],
            "return_types": ["String"],
            "parameters": [{"modifier": "", "type": "String", "name": "value"}],
            "body_types": ["Map<String, String>"],
            "type_parameters": [],
            "type_translations": {
                "return_types": {}, "parameters": {}, "body_types": {},
                "type_parameters": {},
            },
        }
        schema = {
            "classes": {
                "1-6:Demo": {
                    "start": 1,
                    "end": 6,
                    "extends": [],
                    "implements": [],
                    "type_parameters": [],
                    "type_translations": {},
                    "fields": {},
                    "methods": {"2-5:run": method},
                }
            }
        }
        rows = module._build_type_occurrences(schema, code, "Demo.java")
        body = [item for item in rows if item["variation"] == "body_types"]
        self.assertEqual(len(body), 2)
        self.assertEqual({item["start_line"] for item in body}, {3, 4})
        self.assertEqual(len({item["occurrence_id"] for item in body}), 2)
        return_type = next(item for item in rows if item["variation"] == "return_types")
        parameter = next(item for item in rows if item["variation"] == "parameters")
        self.assertGreater(parameter["start_column"], return_type["start_column"])

    def test_codex_runner_parses_thread_and_structured_last_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "out = sys.argv[sys.argv.index('--output-last-message') + 1]\n"
                "open(out, 'w').write(json.dumps({'decisions': []}))\n"
                "print(json.dumps({'type': 'thread.started', 'thread_id': 'thread-123'}))\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            result = CodexRunner(str(executable)).run(
                "prompt", TYPE_DECISIONS_SCHEMA, workspace=root
            )
            self.assertEqual(result.status, "success")
            self.assertEqual(result.session_id, "thread-123")
            self.assertEqual(result.content, {"decisions": []})


if __name__ == "__main__":
    unittest.main()
