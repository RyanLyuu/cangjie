import sys
import unittest
from pathlib import Path

ISOLATION_DIR = Path(__file__).resolve().parents[1] / "src" / "java" / "isolation_validation"
if str(ISOLATION_DIR) not in sys.path:
    sys.path.insert(0, str(ISOLATION_DIR))

import script  # noqa: E402


def _snapshot(type_name: str, **extra: object) -> dict:
    data = {"type": type_name}
    data.update(extra)
    return data


class DependencyStubGenerationTest(unittest.TestCase):
    def test_static_and_global_dependency_signatures_are_supported(self) -> None:
        static_sig, static_reason = script.dependency_stub_signature(
            {
                "method_name": "demo.DependencyService.isEnabled",
                "modifier": "public",
                "Args Initial": [],
            },
            "demo",
        )
        global_sig, global_reason = script.dependency_stub_signature(
            {
                "method_name": "globalCalc",
                "modifier": "public",
                "Args Initial": [("0", {"type": "java.lang.Long", "value": "1"})],
            },
            "demo",
        )

        self.assertEqual(static_sig, "DependencyService.isEnabled()")
        self.assertIsNone(static_reason)
        self.assertEqual(global_sig, "globalCalc(1i64)")
        self.assertIsNone(global_reason)

    def test_arg_receiver_dependency_gets_mock_receiver_and_injection(self) -> None:
        receiver = _snapshot("src.main.demo.Attribute", enum_name="BOLD")
        workflow = [
            {
                "method_name": "demo.Attribute.value",
                "modifier": "public",
                "Return value": {"type": "java.lang.Integer", "value": "1"},
                "Instance Initial": receiver,
                "Instance Final": receiver,
            },
            {
                "method_name": "demo.Focal.run",
                "modifier": "public",
                "Args Initial": [("0", receiver)],
                "Args Final": [("0", receiver)],
                "note": "skip",
            },
        ]

        body = "\n".join(script.build_workflow_body(workflow, "demo"))

        self.assertIn("var arg_0", body)
        self.assertIn("let __dep_receiver_1 = mock<Attribute>()", body)
        self.assertIn("arg_0 = __dep_receiver_1", body)
        self.assertIn("@On(__dep_receiver_1.value())", body)
        self.assertNotIn("mock emission skipped", body)

    def test_field_receiver_dependency_gets_mock_receiver_and_injection(self) -> None:
        repo = _snapshot("src.main.demo.UserRepo", id={"type": "java.lang.Long", "value": "1"})
        workflow = [
            {
                "method_name": "demo.UserRepo.findById",
                "modifier": "public",
                "Args Initial": [("0", {"type": "java.lang.Long", "value": "1"})],
                "Return value": _snapshot("src.main.demo.User", name="Alice"),
                "Instance Initial": repo,
                "Instance Final": repo,
            },
            {
                "method_name": "demo.UserService.getName",
                "modifier": "public",
                "Args Initial": [("0", {"type": "java.lang.Long", "value": "1"})],
                "Instance Initial": {
                    "type": "src.main.demo.UserService",
                    "instance_fields": {"repo": repo},
                },
                "note": "skip",
            },
        ]

        body = "\n".join(script.build_workflow_body(workflow, "demo"))

        self.assertIn("let __dep_receiver_1 = mock<UserRepo>()", body)
        self.assertIn("instance_initial.repo = __dep_receiver_1", body)
        self.assertIn("@On(__dep_receiver_1.findById(1i64))", body)
        self.assertNotIn("mock emission skipped", body)

    def test_unbound_instance_dependency_stays_spec_only(self) -> None:
        workflow = [
            {
                "method_name": "demo.Helper.work",
                "modifier": "public",
                "Return value": {"type": "java.lang.Integer", "value": "1"},
                "Instance Initial": _snapshot("src.main.demo.Helper"),
                "Instance Final": _snapshot("src.main.demo.Helper"),
            },
            {
                "method_name": "demo.Focal.run",
                "modifier": "public",
                "note": "skip",
            },
        ]

        body = "\n".join(script.build_workflow_body(workflow, "demo"))

        self.assertIn("dependencies left as spec-only entries", body)
        self.assertIn("unbound-instance-method-dependency", body)


if __name__ == "__main__":
    unittest.main()
