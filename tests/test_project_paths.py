import tempfile
import unittest
from pathlib import Path

from src.java.utils.project_paths import resolve_java_project_root


class ProjectPathResolutionTest(unittest.TestCase):
    def test_explicit_cleaned_projects_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cleaned_final_projects_variant"
            project = root / "demo"
            project.mkdir(parents=True)
            self.assertEqual(
                resolve_java_project_root("demo", "_ignored", str(root)),
                project,
            )

    def test_explicit_project_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            project.mkdir()
            self.assertEqual(
                resolve_java_project_root("demo", configured_root=str(project)),
                project,
            )


if __name__ == "__main__":
    unittest.main()
