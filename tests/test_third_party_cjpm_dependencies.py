from src.java.translation.create_skeleton import (
    _detect_third_party_dependencies,
    _generate_cjpm_content,
)


def test_third_party_imports_generate_cjpm_dependency():
    libraries = {
        "charset4cj": {
            "dependency": {"git": "https://gitcode.com/Cangjie-TPC/charset4cj.git"},
            "validated_imports": [
                "import charset4cj.*",
            ],
        }
    }
    imports = "import charset4cj.*\nimport std.io.OutputStream\n"

    used = _detect_third_party_dependencies(imports, libraries)
    content = _generate_cjpm_content("jansi", "static", False, libraries, used)

    assert used == {"charset4cj"}
    assert 'charset4cj = { git = "https://gitcode.com/Cangjie-TPC/charset4cj.git" }' in content
