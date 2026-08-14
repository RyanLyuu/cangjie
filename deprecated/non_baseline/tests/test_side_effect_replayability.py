import json
import tempfile
import unittest
from pathlib import Path

from src.java.isolation_validation import side_effect


def _write_case(root: Path, method_body: str, workflow: list[dict]) -> tuple[Path, Path, Path]:
    src = root / "src"
    src.mkdir()
    (src / "Focal.cj").write_text(
        "class Focal {\n"
        "    func run() {\n"
        f"{method_body}\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    test = root / "mock_test.cj"
    test.write_text(
        "package demo.test\n"
        "@Test\n"
        "class MockTest {\n"
        "    @TestCase\n"
        "    func test_mock() {\n"
        "        // focal call: demo.Focal.run\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    workflow_json = root / "mock.workflow.json"
    workflow_json.write_text(json.dumps(workflow), encoding="utf-8")
    return test, workflow_json, src


def _side_effectful_dependency(**extra: object) -> dict:
    dep = {
        "method_name": "demo.Dependency.touch",
        "modifier": "public",
        "occurrence_idx": 0,
        "Static Fields Changed": [{"demo.Dependency": [{"flag": {"type": "java.lang.Boolean", "value": "true"}}]}],
    }
    dep.update(extra)
    return dep


class SideEffectReplayabilityTest(unittest.TestCase):
    def test_allows_instance_method_dependency_without_receiver_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dep = _side_effectful_dependency(
                **{
                    "Instance Initial": {"type": "src.main.demo.Dependency", "instance_fields": {"state": 1}},
                    "Instance Final": {"type": "src.main.demo.Dependency", "instance_fields": {"state": 1}},
                }
            )
            test, workflow, src = _write_case(Path(tmp), "        Dependency.touch()", [dep])

            result = side_effect.analyze_replayability(str(test), str(workflow), str(src))

            self.assertTrue(result["ok"])
            self.assertEqual(result["blockers"], [])

    def test_marks_instance_receiver_mutation_as_not_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dep = _side_effectful_dependency(
                **{
                    "Instance Initial": {"type": "src.main.demo.Dependency", "instance_fields": {"state": 1}},
                    "Instance Final": {"type": "src.main.demo.Dependency", "instance_fields": {"state": 2}},
                }
            )
            test, workflow, src = _write_case(Path(tmp), "        Dependency.touch()", [dep])

            result = side_effect.analyze_replayability(str(test), str(workflow), str(src))

            self.assertFalse(result["ok"])
            self.assertIn(
                side_effect.INSTANCE_METHOD_DEPENDENCY,
                {item["reason"] for item in result["blockers"]},
            )

    def test_marks_expression_side_effect_as_not_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dep = _side_effectful_dependency()
            test, workflow, src = _write_case(Path(tmp), "        let value = Dependency.touch() + 1", [dep])

            result = side_effect.analyze_replayability(str(test), str(workflow), str(src))

            self.assertFalse(result["ok"])
            self.assertIn(
                side_effect.EXPRESSION_SIDE_EFFECT_UNREPLAYABLE,
                {item["reason"] for item in result["blockers"]},
            )

    def test_allows_simple_assignment_call_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dep = _side_effectful_dependency()
            test, workflow, src = _write_case(Path(tmp), "        let value = Dependency.touch()", [dep])

            result = side_effect.analyze_replayability(str(test), str(workflow), str(src))

            self.assertTrue(result["ok"])
            self.assertEqual(result["blockers"], [])

    def test_does_not_treat_focal_declaration_as_dependency_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "Focal.cj").write_text(
                "class Focal {\n"
                "    func touch() {\n"
                "        let value = Dependency.other()\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            test = Path(tmp) / "mock_test.cj"
            test.write_text("// focal call: demo.Focal.touch\n", encoding="utf-8")
            workflow = Path(tmp) / "mock.workflow.json"
            workflow.write_text(json.dumps([_side_effectful_dependency()]), encoding="utf-8")

            result = side_effect.analyze_replayability(str(test), str(workflow), str(src))

            self.assertTrue(result["ok"])
            self.assertEqual(result["blockers"], [])


if __name__ == "__main__":
    unittest.main()
