import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from src.java.translation.compositional_translation_validation import (
    rewrite_static_import_member_access,
)


class StaticImportRewriteTest(unittest.TestCase):
    def test_rewrites_bare_static_imported_members(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp)
            (schema_dir / "demo.Schema.json").write_text(
                json.dumps(
                    {
                        "imports": {
                            "1": {
                                "body": "import static org.fusesource.jansi.internal.Kernel32.FOREGROUND_RED;"
                            },
                            "2": {
                                "body": "import static org.fusesource.jansi.internal.Kernel32.FOREGROUND_GREEN;"
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = Namespace(translation_dir=str(schema_dir))
            fragment = {"schema_name": "demo.Schema"}

            code = "static let x: Int16 = FOREGROUND_RED | Kernel32.FOREGROUND_GREEN"
            rewritten = rewrite_static_import_member_access(code, fragment, args)

            self.assertEqual(
                rewritten,
                "static let x: Int16 = Kernel32.FOREGROUND_RED | Kernel32.FOREGROUND_GREEN",
            )


if __name__ == "__main__":
    unittest.main()
