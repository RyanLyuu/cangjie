import json
import tempfile
import unittest
from pathlib import Path

from src.java.translation.baseline_fragment_translation import _compile_candidate
from src.java.translation.dependency_order import _dependency_first_sccs, fragment_order


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


class BaselineIncrementalCompileTest(unittest.TestCase):
    def _fixture(self, root: Path):
        schema_dir = root / "schemas"
        schema_dir.mkdir()
        skeleton = root / "translation" / "src" / "Demo.cj"
        skeleton.parent.mkdir(parents=True)
        skeleton.write_text(
            "package demo\n\nclass Demo {\n    var value: Int32 = throw Exception('TODO')\n}\n",
            encoding="utf-8",
        )
        schema = {
            "path": "src/main/java/Demo.java",
            "classes": {
                "1-3:Demo": {
                    "fields": {
                        "2-2:value": {
                            "types": ["int"],
                            "type_translations": {
                                "types": {
                                    "int": {
                                        "translated": True,
                                        "translated_target_type": "Int32",
                                    }
                                }
                            },
                        }
                    },
                    "methods": {},
                }
            },
        }
        (schema_dir / "demo.json").write_text(json.dumps(schema), encoding="utf-8")
        fragment = {
            "schema_name": "demo",
            "class_name": "Demo",
            "fragment_name": "2-2:value",
            "fragment_type": "field",
            "signature": "",
            "is_constructor": False,
            "cangjie_translations_skeleton_path": str(skeleton),
        }
        return schema_dir, skeleton, fragment

    def test_failed_build_restores_previous_skeleton(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_dir, skeleton, fragment = self._fixture(root)
            cjpm = root / "cjpm-fail"
            cjpm.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            cjpm.chmod(0o755)
            before = skeleton.read_text()
            success, _ = _compile_candidate(
                "var value: Int32 = 1", [], fragment, schema_dir,
                skeleton.parents[1], str(cjpm), 10,
            )
            self.assertFalse(success)
            self.assertEqual(skeleton.read_text(), before)

    def test_successful_build_keeps_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_dir, skeleton, fragment = self._fixture(root)
            cjpm = root / "cjpm-ok"
            cjpm.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            cjpm.chmod(0o755)
            success, _ = _compile_candidate(
                "var value: Int32 = 1", [], fragment, schema_dir,
                skeleton.parents[1], str(cjpm), 10,
            )
            self.assertTrue(success)
            self.assertIn("var value: Int32 = 1", skeleton.read_text())


if __name__ == "__main__":
    unittest.main()
