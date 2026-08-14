import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ActiveLayoutTest(unittest.TestCase):
    def test_only_baseline_modules_are_active(self) -> None:
        active_java = ROOT / "src" / "java"
        expected = {
            "decomposition",
            "preprocessing",
            "translation",
            "type_resolution",
            "utils",
        }
        actual = {
            path.name
            for path in active_java.iterdir()
            if path.is_dir() and path.name != "__pycache__"
        }
        self.assertEqual(actual, expected)

    def test_legacy_type_resolution_is_isolated(self) -> None:
        archive = ROOT / "deprecated" / "non_baseline" / "src" / "java"
        self.assertTrue((archive / "type_resolution").is_dir())
        active = ROOT / "src" / "java" / "type_resolution"
        self.assertTrue(active.is_dir())
        self.assertFalse((active / "translate_type_rag.py").exists())
        self.assertFalse((active / "interface_shim.py").exists())
        self.assertFalse((active / "type_expression.py").exists())
        self.assertFalse((ROOT / "scripts" / "java" / "translate_types.sh").exists())

    def test_legacy_translation_and_retrieval_code_is_isolated(self) -> None:
        active = ROOT / "src" / "java"
        for name in (
            "analysis", "crawler", "generics_rule_lib", "isolation_validation",
            "model", "postprocessing", "progressive_kb", "rag", "static_analysis",
        ):
            self.assertFalse((active / name).exists())
        translation = active / "translation"
        for name in (
            "cangjie_compilation_validation.py",
            "compositional_translation_validation.py",
            "grammar_prompt.py",
            "prompt_generator.py",
        ):
            self.assertFalse((translation / name).exists())

    def test_type_skill_is_active(self) -> None:
        skill = ROOT / "resolve-cangjie-types" / "SKILL.md"
        self.assertTrue(skill.is_file())

    def test_enhanced_skill_is_self_contained(self) -> None:
        package = ROOT / "resolve-cangjie-types" / "type_resolution"
        self.assertTrue((package / "core.py").is_file())
        script = (ROOT / "resolve-cangjie-types" / "scripts" / "resolve_types.py").read_text()
        self.assertIn("from type_resolution.cli import main", script)

    def test_baseline_does_not_import_enhanced_skill(self) -> None:
        active = ROOT / "src" / "java" / "type_resolution"
        self.assertFalse((active / "core.py").exists())
        skeleton = (ROOT / "src" / "java" / "translation" / "create_skeleton.py").read_text()
        self.assertNotIn("schema_adapter", skeleton)
        self.assertNotIn("resolution.target", skeleton)

    def test_preprocessing_entry_points_exist(self) -> None:
        scripts = ROOT / "scripts" / "java"
        for name in (
            "preprocess.sh",
            "preprocess_evo_cleaned.sh",
            "preprocess_evosuite_cleaned_base.sh",
            "create_schema.sh",
            "get_dependencies.sh",
            "create_skeleton.sh",
            "translate_fragment.sh",
        ):
            self.assertTrue((scripts / name).is_file())

    def test_legacy_entry_points_are_not_active(self) -> None:
        scripts = ROOT / "scripts" / "java"
        for name in (
            "analyze_errors.sh",
            "build_mock_corpus.sh",
            "build_syntax_graph_index.sh",
            "crawl_java_base.sh",
            "decompose_test.sh",
            "extract_coverage.sh",
            "run_ablation.sh",
            "translate_types.sh",
        ):
            self.assertFalse((scripts / name).exists())


if __name__ == "__main__":
    unittest.main()
