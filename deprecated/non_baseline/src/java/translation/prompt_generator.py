import json
import os

from src.java.rag import get_rag_engine
from src.java.progressive_kb import get_progressive_kb
from src.java.translation.grammar_prompt import get_grammar_prompt
from src.java.rag.syntax_graph import get_syntax_graph_rag


def find_class_key(classes_dict, class_name):
    """Find a class key that matches the given class_name pattern.

    Handles both full keys (e.g., '4-26:BaseClass') and simple names (e.g., 'BaseClass').
    """
    for key in classes_dict:
        if key == class_name or key.endswith(f":{class_name}"):
            return key
    return None


def find_method_key(methods_dict, method_name):
    """Find a method key that matches the given method_name pattern.

    Handles both full keys (e.g., '11-13:methodName') and simple names (e.g., 'methodName').
    """
    for key in methods_dict:
        if key == method_name or key.endswith(f":{method_name}"):
            return key
    return None


def extract_actual_name(fragment_name: str) -> str:
    """Extract actual name from fragment/class name with line prefix like '4-38:BaseClass' -> 'BaseClass'"""
    if ":" in fragment_name:
        return fragment_name.split(":")[-1]
    return fragment_name


def render_lines(value, *, partial=False):
    """Render schema translation fields without splitting strings into characters."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        text = ("" if partial else "\n").join(str(item) for item in value)
    else:
        text = str(value)
    return text.replace("<placeholder>", "None" if partial else "")


def render_translation_or_partial(translation, partial_translation):
    if translation:
        return render_lines(translation)
    return render_lines(partial_translation, partial=True)


class PromptGenerator:

    def __init__(
        self, is_feedback, args, fragment_details, feedback="",
        use_icl_pool=False, pseudocode="", _skip_prompt_build=False,
    ):
        self.is_feedback = is_feedback
        self.args = args
        self.prompt = ""
        self.feedback = feedback
        self.prompt_status = "success"
        self.use_icl_pool = use_icl_pool
        self.rag_context: str = ""
        self.kb_context: str = ""
        self.fragment_details = fragment_details
        self.signature = None
        # Pre-populated so context loaders that read it before load_fragment()
        # runs (or when _skip_prompt_build short-circuits the run) see "" instead
        # of raising AttributeError; load_fragment() overwrites it with the real
        # Java fragment text.
        self.source_fragment_body: str = ""
        self.type_resolution_context: str = ""

        # --- Semantic bridge context (set before build_base_prompt is called) ---
        # Part 1: pseudocode intermediate layer (LLM-authored, language-agnostic).
        # The translate() loop populates this when --use_pseudocode is enabled so
        # the translator step focuses on target-language rendering rather than
        # re-importing Java source patterns that have no Cangjie equivalent.
        self.pseudocode_context: str = pseudocode or ""

        # --- Part 2: Cangjie grammar / EBNF prompt injection ------------------
        # When --use_grammar_prompt is on, the EBNF excerpt + runtime type
        # mapping notes act as a hard-syntax reminder for a low-resource target
        # language. Inspired by Grammar Prompting (Wang et al., ACL 2023) which
        # shows that *just* including the grammar in the prompt — no constrained
        # decoding needed — already substantially raises syntactic correctness.
        self.grammar_context: str = ""
        if getattr(args, 'use_grammar_prompt', 'false') == 'true':
            try:
                self.grammar_context = get_grammar_prompt()
            except Exception as e:
                print(f"[Grammar Prompt] Warning: grammar injection failed: {e}")

        # --- Part 3: Syntax-graph RAG ---------------------------------------
        # Placeholder; filled after load_fragment() runs (below) so the Java
        # fragment text is available. Kept here as a declared field so the
        # _skip_prompt_build short-circuit still leaves it set (to "").
        self.syntax_graph_context: str = ""

        self.meta_data = {
            "deepseek-coder-33b-instruct-persona": "You are an AI programming assistant, utilizing the DeepSeek Coder model, developed by DeepSeek Company, and you only answer questions related to computer science. For politically sensitive questions, security and privacy issues, and other non-computer science questions, you will refuse to answer.",
            "deepseek-chat-persona": "",
            "gpt-4o-2024-11-20-persona": "",
            "glm-5.1-persona": "",
            "llama-3-3-70b-instruct-persona": "",
            "Qwen2.5-Coder-32B-Instruct-persona": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
            "cangjie-persona": """You are a Java to Cangjie code translation expert.
Preserve the semantics of the Java fragment while producing idiomatic Cangjie.
Treat every type, generic constraint, import, and public signature supplied by
the resolved skeleton as frozen. Do not independently remap types or change a
signature; report an incompatible type contract instead.""",
            "translation_notes": {
                "field": "Java field translation pattern:\nJava: public int x;\nCangjie: var x: Int64 = 0\n",
                "method": "Java method translation pattern:\nJava: public int add(int a, int b) { return a + b; }\nCangjie: public func add(a: Int64, b: Int64): Int64 { return a + b }\n",
                "static_initializer": "Java static initializer pattern:\nJava: static { count = 10; }\nCangjie: static init() { count = 10 }\n",
            },
        }

        # The new agent-based type stage may attach assertion/API context to the
        # schema later. The legacy type-resolution artifact is intentionally not
        # loaded by the translation stage.
        self.assert_map = {}

        self.load_fragment(fragment_details)

        # Used by _generate_pseudocode() in compositional_translation_validation.py:
        # we only want load_fragment() + the source-fragment assembly, NOT the
        # expensive context loads (RAG/KB/generics/grammar/syntax-graph) nor the
        # ICL pool / full prompt build. Skipping here avoids an extra round-trip
        # of work and, importantly, avoids a second RAG fetch we would otherwise
        # make just to throw away.
        if _skip_prompt_build:
            return

        self.construct_adaptive_icl()

        # RAG context injection
        if getattr(self.args, 'use_rag', 'false') == 'true':
            try:
                rag = get_rag_engine()
                context = rag.inject_fragment_context(self.source_fragment_body)
                if context:
                    self.rag_context = context
            except Exception as e:
                print(f"[RAG] Warning: Fragment RAG injection failed: {e}")

        # Progressive KB context injection (real translation examples > docs)
        if getattr(self.args, 'use_progressive_kb', 'false') == 'true':
            try:
                kb = get_progressive_kb()
                # Retrieve analogous translation pairs for few-shot context
                involved_types = getattr(self, '_involved_types', [])
                examples = kb.retrieve(
                    java_code=self.source_fragment_body,
                    java_types=involved_types,
                    top_k=3,
                )
                if examples:
                    kb_few_shot = kb.format_few_shot_prompt(examples, max_examples=3)
                    if kb_few_shot:
                        self.kb_context = kb_few_shot
            except Exception as e:
                print(f"[Progressive KB] Warning: KB injection failed: {e}")

        # --- Part 3: Syntax-graph RAG ---------------------------------------
        # When --use_syntax_rag is on, retrieve Cangjie corpus snippets whose
        # CFG/DFG fingerprints are structurally similar to the Java fragment and
        # inject them as few-shot structural examples. Inspired by CodeGRAG
        # (Huang et al., 2024); pragmatic non-NN approximation using regex
        # structural fingerprints + Jaccard similarity. Runs after load_fragment
        # so source_fragment_body is populated.
        if getattr(self.args, 'use_syntax_rag', 'false') == 'true':
            try:
                sgrag = get_syntax_graph_rag()
                block = sgrag.inject(self.source_fragment_body or "", top_k=3)
                if block:
                    self.syntax_graph_context = block
            except Exception as e:
                print(f"[Syntax Graph RAG] Warning: injection failed: {e}")

        self.build_base_prompt()

    def build_base_prompt(self):
        self.prompt += self.meta_data[f"{self.args.model}-persona"]
        self.double_line_break()

        # instruction first — LLM sees the task immediately
        self.add_instruction()
        self.double_line_break()

        # Part 2: Cangjie grammar reference — appears right after the task
        # instruction and before the Java source, so the model reads the
        # hard-syntax constraints first and frames the upcoming source code in
        # their light.
        if self.grammar_context:
            self.prompt += self.grammar_context
            self.double_line_break()

        # then Java source code
        self.add_source_code()
        self.double_line_break()

        if self.type_resolution_context:
            self.prompt += self.type_resolution_context
            self.double_line_break()

        # Part 1: Semantic bridge (pseudocode intermediate layer) — appears after
        # the source code so the translator can resolve ambiguities against the
        # Java, but is guided to render the *intent* in idiomatic Cangjie rather
        # than mimic Java syntax line-by-line.
        if self.pseudocode_context:
            self.add_pseudocode_bridge()
            self.double_line_break()

        # then partial Cangjie translation (skeleton with dependencies)
        self.add_partial_translation()
        self.double_line_break()

        # Progressive KB few-shot examples (real translation pairs) — before docs
        if self.kb_context:
            self.prompt += self.kb_context
            self.double_line_break()

        # RAG documentation after the task context, not before
        if self.rag_context:
            self.prompt += "### Reference Cangjie documentation:\n"
            self.prompt += self.rag_context
            self.double_line_break()

        # Part 3: structural examples (CFG/DFG-matched Cangjie corpus snippets)
        if self.syntax_graph_context:
            self.prompt += self.syntax_graph_context
            self.double_line_break()

        # ICL examples after everything else
        if self.adaptive_icl:
            self.prompt += self.adaptive_icl
            self.double_line_break()

        # error feedback at the end (only in feedback loop)
        if self.is_feedback:
            self.add_incorrect_translation()
            self.double_line_break()
            self.add_feedback()
            self.double_line_break()

        self.add_target_translation()

    def construct_adaptive_icl(self):
        used_assertions = []
        for source_assert in self.assert_map:
            if source_assert in self.source_fragment_body:
                used_assertions.append(source_assert)

        source_statements = ""
        target_statements = ""
        for source_assert in self.assert_map:
            if source_assert not in used_assertions:
                continue
            for i in range(2):
                source_statements += (
                    self.assert_map[source_assert][i]["java"] + ";\n        "
                )
                target_statements += (
                    self.assert_map[source_assert][i]["cangjie"] + "\n        "
                )

        if self.is_feedback:
            if used_assertions:
                test_icl = (
                    'Java code:\n```\npublic class TestClass {\n    @Test\n    public void testMethod(self) {\n        List<String> inputList = Arrays.asList("apple", "banana", "cherry");\n        assertEquals("inputList size does not match expected size = 3", 3, inputList.size());\n    '
                    + '}\n}\n```\n\nIncorrect Cangjie translation:\n```\nclass TestClass {\n    public func testMethod(): Void {\n        let inputList: Array<String> = ["apple", "banana", "cherry"]\n        @Test.assertEquals("inputList size does not match expected size = 3", 3, inputList.size())\n    }\n```\n\nExecution feedback:\n```\nerror: argument count mismatch\n```\n\nPartial Cangjie translation:\n```\nclass TestClass {\n    public func testMethod(): Void {\n        // TODO: implement\n    }\n}\n```\n\nCangjie method translation:\n```\n    public func testMethod(): Void {\n        let inputList: Array<String> = ["apple", "banana", "cherry"]\n        @Test.assertEquals(3, inputList.size(), "inputList size does not match expected size = 3")\n    }\n```'
                )
                test_icl = test_icl.replace("self.pytest.", "pytest.")
            else:
                test_icl = self.meta_data["translation_notes"][self.fragment_type]
        else:
            if used_assertions:
                test_icl = (
                    "Java code:\n```\npublic class TestClass {\n    @Test\n    public void testMethod(self) {\n        "
                    + source_statements.rstrip()
                    + "\n    "
                    + "}\n}\n```\n\nPartial Cangjie translation:\n```\nclass TestClass {\n    public func testMethod(): Void {\n        // TODO: implement\n    }\n}\n```\n\nCangjie method translation:\n```\n    public func testMethod(): Void {\n        "
                    + target_statements.rstrip()
                    + "\n```\n"
                )
                test_icl = test_icl.replace("self.pytest.", "pytest.")
            else:
                self.adaptive_icl = self.meta_data["translation_notes"].get(
                    self.fragment_type, ""
                )
                return  # Early return since we set adaptive_icl directly

        if self.is_feedback:
            if used_assertions:
                self.adaptive_icl = test_icl
            else:
                self.adaptive_icl = self.meta_data["translation_notes"].get(
                    self.fragment_type, ""
                )
        else:
            if used_assertions:
                self.adaptive_icl = test_icl
            else:
                self.adaptive_icl = self.meta_data["translation_notes"].get(
                    self.fragment_type, ""
                )

    def load_fragment(self, fragment_details):
        self.schema_name = fragment_details["schema_name"]
        self.class_name = fragment_details["class_name"]
        self.fragment_name = fragment_details["fragment_name"]

        self.class_actual_name = extract_actual_name(self.class_name)
        self.fragment_actual_name = extract_actual_name(self.fragment_name)
        self.fragment_type = fragment_details["fragment_type"]
        self.is_test_method = fragment_details["is_test_method"]

        self.schema_data = {}
        with open(
            f"{self.args.translation_dir}/{self.schema_name}.json", "r"
        ) as f:
            self.schema_data = json.load(f)

        class_key = find_class_key(self.schema_data["classes"], self.class_name)
        if class_key:
            self.fragment_dict = self.schema_data["classes"][class_key].get(
                f"{self.fragment_type}s", {}
            ).get(self.fragment_name, {})
            self.class_dict = self.schema_data["classes"][class_key]
        else:
            self.fragment_dict = {}
            self.class_dict = {"fields": {}, "methods": {}, "nests": [], "nested_inside": [], "extends": [], "cangjie_class_declaration": f"class {self.class_name} {{\n"}

        if "partial_translation" not in self.fragment_dict:
            self.fragment_dict["partial_translation"] = []


        self.source_fragment_body = (
            "\n".join(
                [
                    f"    @{x}"
                    for x in self.class_dict["methods"][
                        self.fragment_name
                    ]["annotations"]
                    if x.startswith("Test")
                ]
            )
            + "\n"
            if self.fragment_type == "method"
            else ""
        )
        if "body" in self.fragment_dict:
            self.source_fragment_body += "".join(self.fragment_dict["body"])

        self.source_class_dependent_fields = ""
        for field in self.class_dict["fields"]:
            if field == self.fragment_name:
                continue
            if field.split(":")[1] in self.source_fragment_body:
                self.source_class_dependent_fields += "".join(
                    self.class_dict["fields"][field][
                        "body"
                    ]
                )
                self.source_class_dependent_fields += "\n"

        self.source_fragment_code = f"class {self.class_actual_name} {{\n{self.source_class_dependent_fields}\n{self.source_fragment_body}\n}}"
        self.type_resolution_context = self._build_type_resolution_context()

    def _build_type_resolution_context(self):
        """Render requirements/guidance from the same finalized records as the skeleton."""
        rows = []
        containers = [self.class_dict, self.fragment_dict]
        for container in containers:
            for variation, slots in container.get("type_translations", {}).items():
                if not isinstance(slots, dict):
                    continue
                for identifier, slot in slots.items():
                    resolution = slot.get("resolution", {}) if isinstance(slot, dict) else {}
                    if resolution.get("status") != "resolved":
                        continue
                    target = resolution.get("target") or {}
                    target_type = str(target.get("type", "")).strip()
                    requirements = [str(item) for item in resolution.get("usage_requirements", [])]
                    guidance = [str(item) for item in resolution.get("translation_guidance", [])]
                    if not requirements and not guidance:
                        continue
                    rows.append(
                        {
                            "variation": variation,
                            "identifier": identifier,
                            "target_type": target_type,
                            "usage_requirements": requirements,
                            "translation_guidance": guidance,
                        }
                    )
        if not rows:
            return ""
        rows.sort(key=lambda item: (item["variation"], item["identifier"]))
        return "### Finalized type usage contract\n" + json.dumps(
            rows, ensure_ascii=False, indent=2
        )

    def add_instruction(self):
        main_note = ""
        if self.fragment_actual_name == "main":
            main_note = "\n\nNote: For the 'main' function in Cangjie, do NOT use 'func' keyword. Use the format: main(args: Array<String>): Int32 { ... }"

        syntax_note = "\n\nIMPORTANT: Use COLON (:) for return type in function signatures, NOT arrow (->). Example: func foo(): Int64 { ... } NOT func foo() -> Int64 { ... }"

        json_instruction = "\n\nYou MUST output ONLY valid JSON (no markdown, no code fences). The JSON must have these fields:\n- 'class': (optional) the complete class definition\n- 'method': ONLY the translated method (with signature). This field will be inserted into the skeleton.\n- 'reasoning': (optional) your reasoning about the translation\n- 'imports': (optional) any additional imports needed as a comma-separated string"

        if self.is_feedback:
            self.prompt += f'### Instruction:\nBased on the feedback provided, identify the error in the following Cangjie translation of the {self.fragment_type} and correct it. You only need to correct the "{self.fragment_actual_name}" {self.fragment_type}. All necessary dependencies are available in partial Cangjie translation. Only complete the given "{self.fragment_actual_name}" method.{main_note}{syntax_note}{json_instruction}'
        else:
            self.prompt += f'### Instruction:\nTranslate the following {self.args.from_lang} {self.fragment_type} to Cangjie. You only need to translate the "{self.fragment_actual_name}" {self.fragment_type}. All necessary dependencies are available in partial Cangjie translation.{main_note}{syntax_note}{json_instruction}'

    def add_source_code(self):
        self.prompt += (
            f"{self.args.from_lang} code:\n```\n{self.source_fragment_code}\n```"
        )

    def add_pseudocode_bridge(self):
        """Part 1: Inject the LLM-authored pseudocode semantic bridge.

        The translate() loop in compositional_translation_validation.py runs the
        'Java → pseudocode' LLM call BEFORE constructing this PromptGenerator
        (when --use_pseudocode is enabled) and passes the result in as the
        `pseudocode=` kwarg. Render it here so the 'pseudocode → Cangjie' step
        works from a language-agnostic description of intent + logic rather
        than from raw Java, decoupling 'understand Java semantics' (errors in
        source-syntax inheritance) from 'produce correct Cangjie syntax/API
        usage' (errors in target-language rendering).
        """
        self.prompt += (
            "### Semantic Bridge (pseudocode)\n"
            "The pseudocode below captures the intent and logic of the Java "
            "fragment without using Java-specific syntax. Use it as the "
            "authoritative description of WHAT to translate; fall back to the "
            "Java code only when the pseudocode is ambiguous.\n\n"
            "```\n"
            f"{self.pseudocode_context}\n"
            "```"
        )

    def add_incorrect_translation(self):
        translation = "\n".join(
            self.class_dict[f"{self.fragment_type}s"][
                self.fragment_name
            ]["translation"]
        )
        # Don't wrap main() - it's a top-level function in Cangjie
        if self.fragment_actual_name != "main":
            self.prompt += f"Incorrect {self.args.to_lang} translation:\n```\nclass {self.class_actual_name} {{\n{translation}\n}}\n```"
        else:
            self.prompt += f"Incorrect {self.args.to_lang} translation:\n```\n{translation}\n```"

    def add_feedback(self):
        self.prompt += "Execution feedback:\n```\n"
        self.prompt += self.feedback
        self.prompt += "\n```"

    def add_partial_translation(self):
        self.build_partial_translation()
        self.prompt += (
            f"Partial Cangjie translation:\n```\n{self.partial_translation}\n```"
        )

    def build_partial_translation(self):
        self.partial_translation = "\n".join(
            self.schema_data.get(
                "cangjie_imports", self.schema_data.get("python_imports", [])
            )
        )
        self.partial_translation += "\n\n"

        inner_outer_classes = self.class_dict["nests"] + [
            self.class_dict["nested_inside"]
        ]
        for inner_outer_class in inner_outer_classes:
            if (
                not inner_outer_class
                or "new" in inner_outer_class
                or "{" in inner_outer_class
                or inner_outer_class == []
            ):
                continue

            class_decl = self.schema_data['classes'][inner_outer_class]['cangjie_class_declaration']
            if not class_decl.rstrip().endswith("}"):
                class_decl = class_decl.rstrip() + "\n}"

            inner_outer_classes_py = [class_decl]
            for field in self.schema_data["classes"][inner_outer_class]["fields"]:
                if field.split(":")[1] in "".join(
                    self.class_dict[
                        f"{self.fragment_type}s"
                    ][self.fragment_name]["body"]
                ):
                    field_translation = self.schema_data["classes"][inner_outer_class][
                        "fields"
                    ][field]["translation"]
                    inner_outer_classes_py.append(
                        render_translation_or_partial(
                            field_translation,
                            self.schema_data["classes"][inner_outer_class]["fields"][field]["partial_translation"],
                        )
                    )
                    inner_outer_classes_py.append("\n")

            if len(inner_outer_classes_py) > 0:
                self.partial_translation += "\n".join(inner_outer_classes_py) + "\n\n"

        dependencies = {}
        dependencies_path = (
            f"data/java/dependencies{self.args.suffix}/{self.args.project}/dependencies.json"
        )
        if self.args.translate_evosuite:
            dependencies_path = (
                f"data/java/dependencies_evosuite/{self.args.project}/dependencies.json"
            )

        with open(dependencies_path, "r") as f:
            dependencies = json.load(f)

        imported_classes = []
        if self.class_name in dependencies:
            imported_classes = dependencies[self.class_name]

        for dependenct_class_name, dependent_class_path in imported_classes:

            has_exceptional_import = False
            for exceptional_import in [
                "commons.io",
                "commons.logging",
                "opentest4j",
                "com.google",
                "org.evosuite",
                "scaffolding",
            ]:
                if exceptional_import in dependent_class_path:
                    has_exceptional_import = True
                    break

                if (
                    "joda.convert" in dependent_class_path
                    and self.args.project == "joda-money"
                ):
                    has_exceptional_import = True
                    break

            if has_exceptional_import:
                continue

            imported_class_path = self.get_dependency_path(
                dependent_class_path, self.args.project
            )

            imported_class_data = {}
            with open(
                f"{self.args.translation_dir}/{self.args.project}.{imported_class_path}.json",
                "r",
            ) as f:
                imported_class_data = json.load(f)

            imported_class_key = find_class_key(imported_class_data["classes"], dependenct_class_name)
            class_declaration = imported_class_data["classes"][imported_class_key]["cangjie_class_declaration"]
            if not class_declaration.rstrip().endswith("}"):
                class_declaration = class_declaration.rstrip() + "\n}"

            imported_classes = [class_declaration]

            for field in imported_class_data["classes"][imported_class_key][
                "fields"
            ]:
                if field.split(":")[1] in "".join(
                    self.class_dict[
                        f"{self.fragment_type}s"
                    ][self.fragment_name]["body"]
                ):
                    field_translation = imported_class_data["classes"][
                        imported_class_key
                    ]["fields"][field]["translation"]
                    imported_classes.append(
                        render_translation_or_partial(
                            field_translation,
                            imported_class_data["classes"][imported_class_key]["fields"][field]["partial_translation"],
                        )
                    )

            if len(imported_classes) > 0:
                self.partial_translation += "\n".join(imported_classes) + "\n"

        for super_class in self.class_dict["extends"]:
            super_class_schema = ""
            for schema_file in os.listdir(self.args.translation_dir):
                if schema_file.endswith(f".{super_class}.json"):
                    super_class_schema = schema_file
                    break

            if super_class_schema == "":
                continue

            super_class_data = {}
            with open(f"{self.args.translation_dir}/{super_class_schema}", "r") as f:
                super_class_data = json.load(f)


            if (
                f"class {super_class}:" in self.partial_translation
                or f"class {super_class}(" in self.partial_translation
            ):
                continue

            super_class_key = find_class_key(super_class_data["classes"], super_class)
            super_class_decl = super_class_data["classes"][super_class_key]["cangjie_class_declaration"]
            # Don't close the class here - we'll close it after adding fields

            super_class_declaration = [super_class_decl]
            for field in super_class_data["classes"][super_class_key]["fields"]:
                if field.split(":")[1] in "".join(
                    self.class_dict[
                        f"{self.fragment_type}s"
                    ][self.fragment_name]["body"]
                ):
                    field_translation = super_class_data["classes"][super_class_key][
                        "fields"
                    ][field]["translation"]
                    super_class_declaration.append(
                        render_translation_or_partial(
                            field_translation,
                            super_class_data["classes"][super_class_key]["fields"][field]["partial_translation"],
                        )
                    )
                    super_class_declaration.append("\n")

            # Close the class after all fields have been added
            if len(super_class_declaration) > 1:
                super_class_declaration.append("\n}")

            if len(super_class_declaration) > 0:
                self.partial_translation += "\n".join(super_class_declaration) + "\n\n"

        # cangjie_class_declaration may be missing if create_skeleton crashed mid-run;
        # fall back to a minimal declaration so the pipeline doesn't hard-crash.
        main_class_decl = self.class_dict.get(
            "cangjie_class_declaration",
            f"class {self.class_actual_name} {{\n",
        )
        # Don't close the class here - we'll close it after adding all members
        main_class_partial_translation = main_class_decl

        if "partial_translation" in self.fragment_dict and "throw Exception('TODO')" not in "".join(self.fragment_dict["partial_translation"]):
            self.prompt_status = "translated"

        for field in self.class_dict["fields"]:
            if (
                field.split(":")[1] == self.fragment_actual_name
                and self.fragment_type == "field"
            ):
                continue
            if field.split(":")[1] in "".join(
                "".join(
                    self.class_dict[
                        f"{self.fragment_type}s"
                    ][self.fragment_name]["body"]
                )
            ):
                field_translation = self.class_dict[
                    "fields"
                ][field]["translation"]
                main_class_partial_translation += render_translation_or_partial(
                    field_translation,
                    self.class_dict["fields"][field]["partial_translation"],
                )
                main_class_partial_translation += "\n\n"

        if self.fragment_type == "method":

            if (
                len(
                    self.class_dict["methods"][
                        self.fragment_name
                    ]["calls"]
                )
                != 0
                and self.args.include_call_graph
            ):

                out_of_file_dependencies = []
                out_of_class_dependencies = []
                for callee_schema, callee_class, callee_method in self.class_dict["methods"][self.fragment_name]["calls"]:

                    if callee_schema == "library":
                        continue

                    callee_schema_data = {}
                    with open(
                        f"{self.args.translation_dir}/{callee_schema}.json",
                        "r",
                    ) as f:
                        callee_schema_data = json.load(f)

                    if ":" not in callee_method:
                        continue

                    if callee_schema != self.schema_name:
                        out_of_file_dependencies.append(
                            (callee_schema, callee_class, callee_method)
                        )
                        continue

                    if callee_class != self.class_name:
                        out_of_class_dependencies.append(
                            (callee_schema, callee_class, callee_method)
                        )
                        continue

                    if self.args.include_implementation:
                        method_translation = callee_schema_data["classes"][
                            callee_class
                        ]["methods"][callee_method]["translation"]
                        callee_partial_translation = render_translation_or_partial(
                            method_translation,
                            callee_schema_data["classes"][callee_class]["methods"][callee_method]["partial_translation"],
                        ).rstrip()
                    else:
                        callee_partial_translation = "".join(
                            callee_schema_data["classes"][callee_class]["methods"][
                                callee_method
                            ]["partial_translation"]
                        ).rstrip()

                    main_class_partial_translation += (
                        f"{callee_partial_translation}\n\n"
                    )

                main_class_partial_translation += "".join(
                    self.class_dict["methods"][
                        self.fragment_name
                    ]["partial_translation"]
                ).rstrip()

                if len(out_of_file_dependencies) != 0:
                    ordered_out_of_file_dependencies = {}
                    for (
                        callee_schema,
                        callee_class,
                        callee_method,
                    ) in out_of_file_dependencies:
                        ordered_out_of_file_dependencies.setdefault(callee_schema, [])
                        ordered_out_of_file_dependencies[callee_schema].append(
                            (callee_class, callee_method)
                        )

                    for callee_schema in ordered_out_of_file_dependencies:
                        for (
                            callee_class,
                            callee_method,
                        ) in ordered_out_of_file_dependencies[callee_schema]:

                            callee_schema_data = {}
                            with open(
                                f"{self.args.translation_dir}/{callee_schema}.json",
                                "r",
                            ) as f:
                                callee_schema_data = json.load(f)

                            if (
                                callee_schema_data["classes"][callee_class][
                                    "cangjie_class_declaration"
                                ]
                                not in self.partial_translation
                            ):
                                callee_class_decl = callee_schema_data['classes'][callee_class]['cangjie_class_declaration']
                                if not callee_class_decl.rstrip().endswith("}"):
                                    callee_class_decl = callee_class_decl.rstrip() + "\n}"
                                self.partial_translation += callee_class_decl
                                for field in callee_schema_data["classes"][
                                    callee_class
                                ]["fields"]:
                                    field_translation = callee_schema_data["classes"][
                                        callee_class
                                    ]["fields"][field]["translation"]
                                    self.partial_translation += render_translation_or_partial(
                                        field_translation,
                                        callee_schema_data["classes"][callee_class]["fields"][field]["partial_translation"],
                                    )
                                    self.partial_translation += "\n"

                            self.partial_translation += "\n"

                            if self.args.include_implementation:
                                callee_method_translation = callee_schema_data[
                                    "classes"
                                ][callee_class]["methods"][callee_method]["translation"]
                                self.partial_translation += render_translation_or_partial(
                                    callee_method_translation,
                                    callee_schema_data["classes"][callee_class]["methods"][callee_method]["partial_translation"],
                                ).rstrip()
                            else:
                                self.partial_translation += "".join(
                                    callee_schema_data["classes"][callee_class][
                                        "methods"
                                    ][callee_method]["partial_translation"]
                                ).rstrip()

                            self.partial_translation += "\n\n"

                if len(out_of_class_dependencies) != 0:
                    ordered_out_of_file_dependencies = {}
                    for (
                        callee_schema,
                        callee_class,
                        callee_method,
                    ) in out_of_class_dependencies:
                        ordered_out_of_file_dependencies.setdefault(callee_schema, [])
                        ordered_out_of_file_dependencies[callee_schema].append(
                            (callee_class, callee_method)
                        )

                    for callee_schema in ordered_out_of_file_dependencies:
                        for (
                            callee_class,
                            callee_method,
                        ) in ordered_out_of_file_dependencies[callee_schema]:
                            callee_schema_data = {}
                            with open(
                                f"{self.args.translation_dir}/{callee_schema}.json",
                                "r",
                            ) as f:
                                callee_schema_data = json.load(f)

                            callee_class_decl = callee_schema_data['classes'][callee_class]['cangjie_class_declaration']
                            # Don't close the class here - we'll close it after adding fields/methods
                            self.partial_translation += callee_class_decl
                            for field in callee_schema_data["classes"][callee_class][
                                "fields"
                            ]:
                                field_translation = callee_schema_data["classes"][
                                    callee_class
                                ]["fields"][field]["translation"]
                                self.partial_translation += (
                                    render_translation_or_partial(
                                        field_translation,
                                        callee_schema_data["classes"][callee_class]["fields"][field]["partial_translation"],
                                    )
                                    + "\n"
                                )

                            if self.args.include_implementation:
                                callee_method_translation = callee_schema_data[
                                    "classes"
                                ][callee_class]["methods"][callee_method]["translation"]
                                self.partial_translation += render_translation_or_partial(
                                    callee_method_translation,
                                    callee_schema_data["classes"][callee_class]["methods"][callee_method]["partial_translation"],
                                )
                            else:
                                self.partial_translation += "".join(
                                    callee_schema_data["classes"][callee_class][
                                        "methods"
                                    ][callee_method]["partial_translation"]
                                )

                            # Close the callee class after adding fields/methods
                            self.partial_translation += "\n}"

                            self.partial_translation += "\n\n"

                main_class_partial_translation += "\n"

            else:
                main_class_partial_translation += "".join(
                    self.class_dict["methods"][
                        self.fragment_name
                    ]["partial_translation"]
                ).rstrip()
                main_class_partial_translation += "\n"

        else:
            for method in self.class_dict["methods"]:
                if method.split(":")[1] in "".join(
                    "".join(
                        self.class_dict[
                            f"{self.fragment_type}s"
                        ][self.fragment_name]["body"]
                    )
                ):
                    method_translation = self.class_dict[
                        "methods"
                    ][method]["translation"]
                    if self.args.include_implementation:
                        main_class_partial_translation += render_translation_or_partial(
                            method_translation,
                            self.class_dict["methods"][method]["partial_translation"],
                        )
                    else:
                        main_class_partial_translation += "".join(
                            self.class_dict["methods"][
                                method
                            ]["partial_translation"]
                        ).replace("<placeholder>", "None")
                    main_class_partial_translation += "\n\n"

        if self.fragment_type == "field":
            if "partial_translation" in self.fragment_dict:
                main_class_partial_translation += (
                    "".join(self.fragment_dict["partial_translation"]).replace(
                        "<placeholder>", ""
                    )
                    + "\n"
                )
        elif self.fragment_type == "static_initializer":
            if "partial_translation" in self.fragment_dict:
                main_class_partial_translation += (
                    "".join(self.fragment_dict["partial_translation"]).replace(
                        "<placeholder>", ""
                    )
                    + "\n"
                )

        # Close the class after all members have been added
        if not main_class_partial_translation.rstrip().endswith("}"):
            main_class_partial_translation = main_class_partial_translation.rstrip() + "\n}\n"

        self.partial_translation += main_class_partial_translation

    def add_target_translation(self):
        self.prompt += "### Response:\n"
        self.prompt += 'Output ONLY the JSON object with your translation in the "method" field.'

    def single_line_break(self):
        self.prompt += "\n"

    def double_line_break(self):
        self.prompt += "\n\n"

    def get_dependency_path(self, dependent_class, project):
        if os.path.exists(
            f"java_projects/cleaned_final_projects{self.args.suffix}/{project}/src/main/java/"
            + dependent_class.replace(".", "/")
            + ".java"
        ):
            return f"src.main.{dependent_class}"
        elif os.path.exists(
            f"java_projects/cleaned_final_projects{self.args.suffix}/{project}/src/test/java/"
            + dependent_class.replace(".", "/")
            + ".java"
        ):
            return f"src.test.{dependent_class}"
        else:
            return f"src.main.{dependent_class}"

    def generate_prompt(self):
        self.prompt = self.prompt.replace("\u0000", "")
        return self.prompt
