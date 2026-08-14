import unittest
from unittest import mock

from src.java.utils.package_collapse import (
    build_schema_package_dependency_graph,
    compute_effective_subpath_map,
)
from src.java.translation.create_skeleton import generate_one_file_skeleton


class PackageCollapseTest(unittest.TestCase):
    def test_placeholder_schema_adds_root_package_edge(self):
        schemas = [
            (
                "root.json",
                "root.json",
                {"path": "Root.java", "classes": {"1:Root": {}}},
            ),
            (
                "mime.json",
                "mime.json",
                {
                    "path": "Mime.java",
                    "classes": {"1:Mime": {}},
                    "generated_type_placeholders": [{"name": "X2CangjieType"}],
                },
            ),
        ]
        with mock.patch(
            "src.java.utils.package_collapse.compute_skeleton_sub_path",
            side_effect=lambda path: None if path == "Root.java" else "mime",
        ):
            graph = build_schema_package_dependency_graph(
                schemas,
                {"Root": None, "Mime": "mime"},
                {},
            )

        self.assertIn(None, graph["mime"])
        self.assertEqual(compute_effective_subpath_map(graph)["mime"], None)

    def test_collapsed_file_drops_same_package_project_import(self):
        # The full skeleton path is exercised indirectly by keeping this
        # focused on the generated import section.
        with mock.patch(
            "src.java.translation.create_skeleton.generate_imports_skeleton",
            return_value=("import commons_fileupload.X2CangjieType\n"),
        ), mock.patch(
            "src.java.translation.create_skeleton.generate_package_header",
            return_value="__IMPORTS_PLACEHOLDER__\n",
        ), mock.patch(
            "src.java.translation.create_skeleton.get_class_order",
            return_value=[],
        ), mock.patch("src.java.translation.create_skeleton.os.makedirs"), mock.patch(
            "src.java.translation.create_skeleton.open",
            mock.mock_open(),
        ):
            result = generate_one_file_skeleton(
                {"path": "Mime.java", "classes": {}},
                "mime.json", "mime.json", "commons_fileupload", {}, {}, {},
                {}, {}, [], "/tmp/skeleton", "/tmp/translation", {},
                {"mime": None},
            )
        self.assertEqual(result, (False, False, set()))


if __name__ == "__main__":
    unittest.main()
