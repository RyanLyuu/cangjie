import tempfile
import unittest
from pathlib import Path

from src.java.isolation_validation.test_matcher import find_focal_tests


def _write_test(root: Path, name: str, focal: str, argc: int | None = None, arg_types: str | None = None) -> Path:
    lines = [
        "package jansi.test",
        "",
        f"// focal call: {focal}",
    ]
    if argc is not None:
        lines.append(f"// focal argc: {argc}")
    if arg_types is not None:
        lines.append(f"// focal arg types: {arg_types}")
    lines.extend(
        [
            "@Test",
            f"public func {name}() {{",
            "    return",
            "}",
        ]
    )
    path = root / f"{name}_test.cj"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class FocalTestMatcherTest(unittest.TestCase):
    def test_overload_matching_uses_exact_arg_types_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            attr = _write_test(root, "attr", "org.fusesource.jansi.Ansi.a", 1, "Attribute")
            string = _write_test(root, "string", "org.fusesource.jansi.Ansi.a", 1, "String")
            obj = _write_test(root, "object", "org.fusesource.jansi.Ansi.a", 1, "Object")
            _write_test(root, "int_arg", "org.fusesource.jansi.Ansi.a", 1, "int")

            attr_fragment = {
                "class_name": "Ansi",
                "fragment_name": "a",
                "parameters": [{"type": "Attribute"}],
            }
            self.assertEqual([p for p, _ in find_focal_tests(attr_fragment, root)], [attr])

            object_fragment = {
                "class_name": "Ansi",
                "fragment_name": "a",
                "parameters": [{"type": "Object"}],
            }
            self.assertEqual([p for p, _ in find_focal_tests(object_fragment, root)], [obj])

            charseq_fragment = {
                "class_name": "Ansi",
                "fragment_name": "a",
                "parameters": [{"type": "CharSequence"}],
            }
            self.assertEqual(find_focal_tests(charseq_fragment, root), [])
            self.assertNotIn(string, [p for p, _ in find_focal_tests(object_fragment, root)])

    def test_constructor_matching_uses_init_and_arg_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            no_arg = _write_test(root, "ctor0", "org.fusesource.jansi.Ansi.<init>", 0, "")
            builder = _write_test(root, "ctor_builder", "org.fusesource.jansi.Ansi.<init>", 1, "StringBuilder")

            constructor = {
                "class_name": "Ansi",
                "fragment_name": "Ansi",
                "is_constructor": True,
                "parameters": [],
            }
            self.assertEqual([p for p, _ in find_focal_tests(constructor, root)], [no_arg])

            constructor_with_builder = {
                "class_name": "Ansi",
                "fragment_name": "<init>",
                "is_constructor": True,
                "parameters": [{"type": "StringBuilder"}],
            }
            self.assertEqual([p for p, _ in find_focal_tests(constructor_with_builder, root)], [builder])

    def test_normalizes_inner_classes_and_decomposed_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render = _write_test(root, "render", "org.fusesource.jansi.AnsiRenderer.render", 1, "String")
            inner = _write_test(root, "inner", "org.fusesource.jansi.Ansi$Attribute.value", 0, "")
            private_like = _write_test(root, "private_like", "org.fusesource.jansi.Ansi._appendEscapeSequence", 2, "char,int")

            render_fragment = {
                "class_name": "AnsiRenderer",
                "fragment_name": "render3",
                "parameters": [{"type": "String"}],
            }
            self.assertEqual([p for p, _ in find_focal_tests(render_fragment, root)], [render])

            inner_fragment = {
                "class_name": "Ansi_Attribute",
                "fragment_name": "value",
                "parameters": [],
            }
            self.assertEqual([p for p, _ in find_focal_tests(inner_fragment, root)], [inner])

            public_fragment = {
                "class_name": "Ansi",
                "fragment_name": "appendEscapeSequence",
                "parameters": [{"type": "char"}, {"type": "int"}],
            }
            self.assertEqual(find_focal_tests(public_fragment, root), [])

            private_fragment = {
                "class_name": "Ansi",
                "fragment_name": "_appendEscapeSequence",
                "parameters": [{"type": "char"}, {"type": "int"}],
            }
            self.assertEqual([p for p, _ in find_focal_tests(private_fragment, root)], [private_like])


if __name__ == "__main__":
    unittest.main()
