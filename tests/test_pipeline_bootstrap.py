import tempfile
import unittest
from pathlib import Path

from src.java.utils.parse_dependencies import ensure_compiled_classes
from src.java.utils.project_paths import materialize_call_graph


class PipelineBootstrapTest(unittest.TestCase):
    def test_materializes_checked_in_project_call_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "projects" / "demo"
            project.mkdir(parents=True)
            (project / "callgraph.txt").write_text("M:a:b M:c:d\n", encoding="utf-8")

            result = materialize_call_graph(project, "demo", root / "data")

            self.assertEqual(result, root / "data" / "demo" / "callgraph.txt")
            self.assertEqual(result.read_text(encoding="utf-8"), "M:a:b M:c:d\n")

    def test_existing_classes_skip_maven(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "target/classes").mkdir(parents=True)
            self.assertFalse(
                ensure_compiled_classes(project, "definitely-missing-maven")
            )

    def test_missing_classes_run_maven(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            (project / "pom.xml").write_text("<project/>\n", encoding="utf-8")
            maven = root / "fake-mvn"
            maven.write_text(
                "#!/bin/sh\nmkdir -p target/classes\n",
                encoding="utf-8",
            )
            maven.chmod(0o755)

            self.assertTrue(ensure_compiled_classes(project, str(maven), 10))
            self.assertTrue((project / "target/classes").is_dir())


if __name__ == "__main__":
    unittest.main()
