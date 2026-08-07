from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .models import ProbeResult, TypeDecision, TypeOccurrence


class ProbeUnavailable(RuntimeError):
    pass


@dataclass
class CangjieTypeProbe:
    executable: str = "cjc"
    timeout: int = 60

    def ensure_available(self) -> None:
        if not (shutil.which(self.executable) or Path(self.executable).is_file()):
            raise ProbeUnavailable(f"Cangjie compiler not found: {self.executable}")

    def probe(
        self,
        occurrence: TypeOccurrence,
        decision: TypeDecision,
        *,
        project_types: set[str],
        placeholder_names: tuple[str, ...] = (),
    ) -> ProbeResult:
        self.ensure_available()
        error = self._validate(decision)
        if error:
            return ProbeResult(False, error)

        if self._is_direct_project_type(decision.translated_target_type, project_types):
            return ProbeResult(True, "project type name preserved; isolated probe not required")

        source = self._source(occurrence, decision, placeholder_names)
        with tempfile.TemporaryDirectory(prefix="x2cangjie-type-probe-") as temp_dir:
            root = Path(temp_dir)
            source_path = root / "type_probe.cj"
            output_path = root / "type_probe.out"
            source_path.write_text(source, encoding="utf-8")
            # A type probe is a package compile, not an executable. Static-library
            # output validates declarations and imports without requiring `main`.
            command = (
                self.executable,
                "--output-type",
                "staticlib",
                "-o",
                str(output_path),
                str(source_path),
            )
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return ProbeResult(False, f"type probe timed out after {self.timeout}s", command, source)
            diagnostic = "\n".join(
                part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
            )
            return ProbeResult(completed.returncode == 0, diagnostic, command, source)

    @staticmethod
    def _validate(decision: TypeDecision) -> str:
        if not decision.translated_target_type:
            return "translated_target_type is empty"
        for item in decision.imports:
            for line in item.splitlines():
                if line.strip() and not line.strip().startswith("import "):
                    return f"invalid Cangjie import: {line.strip()}"
        return ""

    @staticmethod
    def _is_direct_project_type(target: str, project_types: set[str]) -> bool:
        value = target.strip().lstrip("?")
        if any(token in value for token in "<[](), "):
            return False
        return value in project_types or value.split(".")[-1] in project_types

    @staticmethod
    def _source(
        occurrence: TypeOccurrence,
        decision: TypeDecision,
        placeholder_names: tuple[str, ...],
    ) -> str:
        imports = []
        for item in decision.imports:
            imports.extend(line.strip() for line in item.splitlines() if line.strip())
        lines = ["package type_probe", *sorted(set(imports)), ""]
        for name in sorted(set(placeholder_names)):
            lines.append(f"interface {name} {{}}")

        target = decision.translated_target_type.strip()
        if occurrence.role == "type-parameter":
            if " where " in target:
                name, constraint = target.split(" where ", 1)
                lines.extend([
                    f"class TypeProbe<{name.strip()}> where {constraint.strip()} {{",
                    f"    var value: {name.strip()} = throw Exception('TODO')",
                    "}",
                ])
            else:
                name = re.split(r"\s+", target, maxsplit=1)[0]
                lines.extend([
                    f"class TypeProbe<{name}> {{",
                    f"    var value: {name} = throw Exception('TODO')",
                    "}",
                ])
        else:
            lines.extend([
                "class TypeProbe {",
                f"    var value: {target} = throw Exception('TODO')",
                "}",
            ])
        return "\n".join(lines) + "\n"
