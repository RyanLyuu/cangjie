import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from src.java.translation.skeleton_mcp_server import (
    TOOL_NAME,
    handle_message,
)
from src.java.translation.skeleton_service import (
    SkeletonRequest,
    _cangjie_environment,
    generate_skeleton,
    receipt_path_for,
)
from src.java.translation.skeleton_stage import (
    SKELETON_STAGE_SCHEMA,
    new_request,
    new_skeleton_runner,
    run_skeleton_stage,
)
from src.java.type_resolution.agent import AgentResult, AgentRunner


class _RecordingRunner(AgentRunner):
    def __init__(self, content):
        self.content = content
        self.prompts = []

    def run(self, prompt, output_schema, *, workspace, session_id=""):
        self.prompts.append((prompt, output_schema, Path(workspace)))
        return AgentResult("success", self.content, session_id="skeleton-session")


class SkeletonMcpTest(unittest.TestCase):
    def request(self, **overrides):
        data = {
            "project": "demo",
            "model": "codex-baseline",
            "temperature": "0.0",
            "suffix": "",
            "include_tests": False,
            "compile_timeout": 10,
            "request_id": str(uuid.uuid4()),
        }
        data.update(overrides)
        return SkeletonRequest.from_dict(data)

    def test_server_advertises_the_single_skeleton_tool(self):
        response = handle_message({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {},
        })
        tools = response["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], [TOOL_NAME])
        self.assertTrue(tools[0]["inputSchema"]["additionalProperties"] is False)

    def test_request_rejects_path_and_non_uuid_values(self):
        with self.assertRaisesRegex(ValueError, "path-safe"):
            self.request(project="../outside")
        with self.assertRaisesRegex(ValueError, "path-safe"):
            self.request(project="..")
        with self.assertRaisesRegex(ValueError, "UUID"):
            self.request(request_id="not-a-uuid")
        with self.assertRaisesRegex(ValueError, "boolean"):
            self.request(include_tests="false")

    def test_cangjie_environment_exposes_runtime_from_sdk_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            sdk = Path(tmp) / "cangjie"
            runtime = sdk / "runtime" / "lib" / "linux_x86_64_cjnative"
            (sdk / "bin").mkdir(parents=True)
            (sdk / "tools" / "bin").mkdir(parents=True)
            runtime.mkdir(parents=True)
            with mock.patch.dict(
                os.environ,
                {"CANGJIE_HOME": str(sdk), "PATH": "/usr/bin", "LD_LIBRARY_PATH": ""},
                clear=False,
            ):
                environment = _cangjie_environment()

            self.assertEqual(environment["CANGJIE_HOME"], str(sdk.resolve()))
            self.assertTrue(environment["PATH"].startswith(f"{sdk}/bin:"))
            self.assertTrue(environment["LD_LIBRARY_PATH"].startswith(str(runtime)))

    def test_tool_refuses_to_generate_for_unresolved_types_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            request = self.request()
            schema_dir = (
                workspace / "data/java/schemas" / request.model
                / request.temperature / request.project
            )
            schema_dir.mkdir(parents=True)
            schema = {
                "path": "projects/demo/src/main/java/example/Demo.java",
                "type_occurrences": [{
                    "occurrence_id": "occ-name",
                    "class_key": "1-2:Demo",
                    "fragment_kind": "field",
                    "fragment_key": "2-2:name",
                    "variation": "types",
                    "identifier": "String",
                    "source_type": "String",
                    "role": "field",
                }],
                "classes": {"1-2:Demo": {
                    "fields": {"2-2:name": {
                        "types": ["String"], "type_translations": {"types": {}},
                    }},
                    "methods": {},
                }},
            }
            (schema_dir / "demo.src.main.example.Demo.json").write_text(
                json.dumps(schema), encoding="utf-8"
            )

            result = generate_skeleton(request, workspace)

            self.assertEqual(result["status"], "unresolved_types")
            self.assertEqual(result["unresolved_occurrences"][0]["occurrence_id"], "occ-name")
            receipt = receipt_path_for(request, workspace)
            stored = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(stored["status"], "unresolved_types")
            self.assertEqual(stored["tool_name"], TOOL_NAME)
            self.assertEqual(stored["tool_call_count"], 1)
            self.assertFalse((workspace / "data/java/skeletons/demo").exists())

    def test_stage_requires_agent_tool_claim_and_matching_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            request = self.request()
            receipt = receipt_path_for(request, workspace)
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({
                "request_id": request.request_id,
                "status": "success",
                "tool_name": TOOL_NAME,
                "tool_call_count": 1,
                "project": request.project,
                "schema_dir": str(
                    workspace / "data/java/schemas" / request.model
                    / request.temperature / request.project
                ),
                "build": {"returncode": 0, "diagnostic": ""},
            }), encoding="utf-8")
            runner = _RecordingRunner({
                "request_id": request.request_id,
                "called_tool": True,
                "build_status": "success",
                "summary": "generated",
            })

            result = run_skeleton_stage(runner, request, workspace=workspace)

            self.assertEqual(result.status, "success")
            self.assertEqual(runner.prompts[0][1], SKELETON_STAGE_SCHEMA)
            self.assertIn(TOOL_NAME, runner.prompts[0][0])

    def test_stage_rejects_an_agent_response_without_a_tool_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = self.request()
            runner = _RecordingRunner({
                "request_id": request.request_id,
                "called_tool": True,
                "build_status": "success",
                "summary": "claimed success",
            })

            result = run_skeleton_stage(runner, request, workspace=tmp)

            self.assertEqual(result.status, "tool_not_called")

    def test_skeleton_runner_registers_the_stdio_mcp_server_with_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            executable = workspace / "fake-codex"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "pathlib.Path('codex-args.json').write_text(json.dumps(sys.argv[1:]))\n"
                "out = sys.argv[sys.argv.index('--output-last-message') + 1]\n"
                "pathlib.Path(out).write_text(json.dumps({\n"
                "  'request_id': '00000000-0000-0000-0000-000000000000',\n"
                "  'called_tool': True, 'build_status': 'success', 'summary': 'ok'\n"
                "}))\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            runner = new_skeleton_runner(
                executable=str(executable), model="", timeout=10, workspace=workspace
            )

            result = runner.run("prompt", SKELETON_STAGE_SCHEMA, workspace=workspace)

            self.assertEqual(result.status, "success")
            args = json.loads((workspace / "codex-args.json").read_text(encoding="utf-8"))
            config_values = [args[index + 1] for index, value in enumerate(args[:-1]) if value == "-c"]
            self.assertTrue(any("mcp_servers.x2cangjie_skeleton.command=" in value for value in config_values))
            self.assertIn(
                'mcp_servers.x2cangjie_skeleton.args=["-m", "src.java.translation.skeleton_mcp_server"]',
                config_values,
            )
            self.assertTrue(any("mcp_servers.x2cangjie_skeleton.cwd=" in value for value in config_values))
            self.assertIn(
                'mcp_servers.x2cangjie_skeleton.tools.generate_cangjie_skeleton.approval_mode="auto"',
                config_values,
            )
            self.assertTrue(any(value.endswith('.trust_level="trusted"') for value in config_values))
            self.assertEqual(args[args.index("--sandbox") + 1], "workspace-write")
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", args)

    def test_new_request_is_validated_before_it_reaches_an_agent(self):
        with self.assertRaisesRegex(ValueError, "path-safe"):
            new_request(
                project="../outside", model="m", temperature="0.0", suffix="",
                include_tests=False, compile_timeout=10,
            )


if __name__ == "__main__":
    unittest.main()
