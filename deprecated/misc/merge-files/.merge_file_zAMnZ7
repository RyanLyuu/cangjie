import argparse
import contextlib
import json
import os
import re
import yaml
import subprocess
import tempfile
from datetime import datetime
from src.java.model.model import Model
from jinja2 import Template

from src.java.rag import get_rag_engine
from src.java.progressive_kb import get_progressive_kb
from src.java.generics_rule_lib import get_generics_rule_lib
from src.java.utils.get_custom_types import (
    dedupe_preserve_order,
    get_custom_type_translation_map,
    get_custom_types,
    save_custom_types,
)


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _should_include_test_sources(args):
    return _as_bool(getattr(args, 'translate_tests', 'false'))


def _is_test_schema_name(schema_file):
    return (
        '.src.test.' in schema_file
        or schema_file.endswith('.src.test.json')
        or '.evosuite-tests.' in schema_file
    )


class TypePromptGenerator:
    def __init__(self, context_code_snippet, fragment_type, source_type, source_type_description, type_variation, prompt_type, source_language, target_language, feedback):
        self.context_code_snippet = context_code_snippet
        self.fragment_type = fragment_type
        self.source_type = source_type if type_variation in ['FIELD TYPE', 'RETURN TYPE', 'METHOD BODY TYPE'] else source_type['type']
        self.source_type_description = source_type_description
        self.type_variation = type_variation
        self.prompt_type = prompt_type
        self.source_language = source_language
        self.target_language = target_language
        self.feedback = feedback
        self.prompt = ''

        self.prompt_template_config = yaml.safe_load(open('configs/prompt_templates.yaml', 'r'))

    def generate_prompt(self):
        self.prompt += self.add_instance_prompt()
        self.prompt += '\n\n'
        if self.feedback != '':
            self.prompt += self.add_feedback_prompt()
            self.prompt += '\n\n'
        self.prompt += self.add_response_format_prompt()
        return self.prompt

    def add_instance_prompt(self):
        template = Template(self.prompt_template_config['templates'][f'type_resolution_{self.prompt_type}_instance'])
        return template.render(**self.__dict__)

    def add_feedback_prompt(self):
        template = Template(self.prompt_template_config['templates'][f'type_resolution_{self.prompt_type}_feedback'])
        return template.render(**self.__dict__)

    def add_response_format_prompt(self):
        template = Template(self.prompt_template_config['templates'][f'type_resolution_{self.prompt_type}_response_format'])
        return template.render(**self.__dict__)


class Interaction:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class Result:
    def __init__(self):
        self.identifier = ''
        self.translated = False
        self.attempted = False
        self.type_variation = ''
        self.timestamp = ''
        self.source_type = ''
        self.generation = ''
        self.imports = ''
        self.translated_target_type = ''
        self.reasoning = ''
        self.prompt = ''
        self.feedback = ''


class Parser:
    def extract_imports(self, text):
        pattern = re.search(r'CANGJIE IMPORTS:\s*```(?:cangjie)?\s*(.*?)\s*```', text, re.DOTALL)
        return pattern.group(1).strip() if pattern else None

    def extract_translation(self, text):
        pattern = re.search(r'CANGJIE TRANSLATION:\s*```(?:cangjie)?\s*(.*?)\s*```', text, re.DOTALL)
        return pattern.group(1).strip() if pattern else None

    def extract_reasoning(self, text):
        pattern = re.search(r'REASONING:\s*(.*?)(?=\n\n|$)', text, re.DOTALL)
        return pattern.group(1).strip() if pattern else None

    def parse_response(self, generation):
        imports = self.extract_imports(generation)
        translation = self.extract_translation(generation)
        reasoning = self.extract_reasoning(generation)
        return imports, translation, reasoning


# Cangjie types that are built-in and require no import statements.
# When imports is None but the translated type is one of these,
# we accept it as a legitimate "no imports needed" result.
CANGJIE_BUILTIN_TYPES = {
    'Int8', 'Int16', 'Int32', 'Int64', 'IntNative',
    'UInt8', 'UInt16', 'UInt32', 'UInt64', 'UIntNative',
    'Float16', 'Float32', 'Float64',
    'Bool', 'Unit', 'Nothing',
    'Byte',
    'String', 'Rune',
    'Any', 'Object', 'Comparable',
    'Array', 'ArrayList', 'HashMap', 'HashSet', 'LinkedList', 'RSortSet',
    'Option', 'Result', 'Optional',
    'BigInteger', 'BigDecimal', 'Decimal',
    'Iterator', 'Iterable', 'Collection', 'Sequence',
    'Range', 'Int64Range',
    'Throwable', 'Exception', 'Error',
    'Ordering',
}


def _strip_generic_params(type_str):
    """Strip generic type parameters from a type string for built-in matching.
    e.g. 'HashMap<String, Int64>' -> 'HashMap', 'Option<T>' -> 'Option'
    """
    if '<' in type_str:
        return type_str.split('<', 1)[0].strip()
    if '[' in type_str:
        return type_str.split('[', 1)[0].strip()
    return type_str.strip()


def get_source_type_description(source_type):
    source_type = source_type.strip()
    if '[' in source_type:
        source_type = source_type.split('[')[0]
    if '<' in source_type:
        source_type = source_type.split('<')[0]
    type_documentation = {}
    with open('data/java/crawl/java.base_module_doc.json') as f:
        type_documentation = json.load(f)

    for module_name in type_documentation:
        for package_name in type_documentation[module_name]:
            for class_name in type_documentation[module_name][package_name]:
                if source_type in type_documentation[module_name][package_name][class_name]:
                    if 'description' in type_documentation[module_name][package_name][class_name][source_type]:
                        return type_documentation[module_name][package_name][class_name][source_type]['description']
                    return ''

    return ''


def append_result(data, class_, fragment_type, fragment, type_variation, type_, result):
    type_identifier = type_ if type_variation in ['types', 'return_types', 'body_types'] else f'{type_["modifier"]}|{type_["type"]}|{type_["name"]}'
    data['classes'][class_][f'{fragment_type}s'][fragment]['type_translations'][type_variation][type_identifier] = result.__dict__
    return data

def save_results(data, schema_dir, schema_file):
    with open(f'{schema_dir}/{schema_file}', 'w') as f:
        json.dump(data, f, indent=4)


def init_type_resolution_log(args):
    log_dir = os.path.join('logs', 'type_resolution')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(
        log_dir,
        f'{args.project_name}_{args.model_name}_{args.temperature}_type_resolution.log',
    )
    with open(log_path, 'a') as f:
        f.write('\n' + '=' * 80 + '\n')
        f.write(f'Type resolution run started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'project={args.project_name}, model={args.model_name}, temperature={args.temperature}\n')
        f.write('=' * 80 + '\n')
    return log_path


def log_detail(log_path, title, content=''):
    with open(log_path, 'a') as f:
        f.write(f'\n{"=" * 24} {title} {"=" * 24}\n')
        if content is not None:
            f.write(str(content))
            if not str(content).endswith('\n'):
                f.write('\n')


def count_pending_type_translations(schema_dir, include_tests=False):
    total = 0
    type_variations = ['types', 'return_types', 'parameters', 'body_types']
    for schema_file in os.listdir(schema_dir):
        if _is_test_schema_name(schema_file) and not include_tests:
            continue
        with open(f'{schema_dir}/{schema_file}', 'r') as f:
            data = json.load(f)
        for class_ in data['classes']:
            for fragment_type in ['field', 'method']:
                for fragment in data['classes'][class_][f'{fragment_type}s']:
                    for type_variation in type_variations:
                        if fragment_type == 'field' and type_variation != 'types':
                            continue
                        if fragment_type == 'method' and type_variation == 'types':
                            continue
                        for type_ in data['classes'][class_][f'{fragment_type}s'][fragment][type_variation]:
                            type_identifier = type_ if type_variation in ['types', 'return_types', 'body_types'] else f'{type_["modifier"]}|{type_["type"]}|{type_["name"]}'
                            if not data['classes'][class_][f'{fragment_type}s'][fragment]['type_translations'][type_variation][type_identifier]['translated']:
                                total += 1
    return total


def terminal_type_status(index, total, source_type, target_type, passed, reason):
    icon = '✅' if passed else '❌'
    target = target_type if target_type else '<not written>'
    width = max(3, len(str(total)))
    print(f'[type {index:0{width}d}/{total:0{width}d}] {icon} {source_type} -> {target} | {reason}', flush=True)


def _is_type_parameter(source_type):
    """Check if source_type is a Java type parameter declaration (single uppercase letter like T, E, K, V).

    Type parameters should be preserved as-is, not mapped to Any.
    Common Java type parameter names: T, E, K, V, U, R, S, N, A, B, C, M, X, Y, Z.
    """
    if not source_type:
        return False
    # Strip whitespace
    stripped = source_type.strip()
    # Pure single uppercase letter (T, E, K, V)
    if len(stripped) == 1 and stripped.isalpha() and stripped.isupper():
        return True
    # Common multi-letter type parameter patterns (T1, T2, E1, TKey, VVal) -
    # these start with uppercase and are likely type parameters, not class names.
    # Only match short all-uppercase identifiers that look like type parameters.
    # Most classes have mixed case (ArrayList, HashMap) while type params are all-uppercase or short.
    if stripped.isupper() and len(stripped) <= 3:
        return True
    # Angle-bracket type parameter patterns like <K, V> or <T> should not appear here,
    # but if they do, they're definitely type parameters
    if stripped.startswith('<') or stripped.endswith('>'):
        return True
    return False


def fallback_type_for(source_type):
    """Determine a fallback Cangjie type for a Java type when no other mapping is available.

    Priority order:
    1. Type parameters (T, E, K, V) → preserve as-is (not Any!)
    2. Array types (T[]) → Array<Any>
    3. Rule lib nested class lookup (Map.Entry → MapEntry)
    4. Rule lib primitive_map lookup (ThreadFactory, Instant, etc.)
    5. Rule lib functional interface lookup (Function<T,R> → (T) -> R)
    6. Container bare-name lookup (List, Map, etc.)
    7. Container with generics (List<Something>) → resolve via rule lib
    8. Default → Any
    """
    if not source_type:
        return 'Any'

    # 1. Type parameters should be preserved, never mapped to Any
    if _is_type_parameter(source_type):
        return source_type.strip()

    # 2. Array types
    if source_type.endswith('[]'):
        return 'Array<Any>'

    stripped = source_type.strip()
    # Strip package qualifier for lookup
    short_name = stripped.split('.')[-1] if '.' in stripped else stripped

    # 3-7. Check rule lib for static type mappings (no LLM needed)
    try:
        rule_lib = get_generics_rule_lib()

        # 3. Nested class lookup (Map.Entry → MapEntry)
        if '.' in stripped:
            nested = rule_lib.translate_nested_class(stripped)
            if nested is not None:
                return nested

        # 4. Primitive map lookup (JDK type → Cangjie type)
        if short_name in rule_lib.primitive_map:
            return rule_lib.primitive_map[short_name]
        if stripped in rule_lib.primitive_map:
            return rule_lib.primitive_map[stripped]

        # 5. Functional interface lookup
        func_type = rule_lib.translate_functional_interface(stripped)
        if func_type is not None:
            return func_type

        # 6. Container bare-name lookup
        container_entry = rule_lib.get_container_cangjie(short_name)
        if container_entry is not None:
            return container_entry['cangjie']

        # 7. Container with generics
        if '<' in stripped and stripped.endswith('>'):
            translated = rule_lib.translate_container_type(stripped)
            if translated is not None:
                return translated
    except Exception:
        pass  # Rule lib not available, fall through

    return 'Any'


def _cangjie_stub_name(type_name):
    simple_name = type_name.split('.')[-1]
    simple_name = re.sub(r'[^0-9A-Za-z_]', '_', simple_name)
    if not simple_name:
        return ''
    if simple_name[0].isdigit():
        simple_name = f'_{simple_name}'
    return simple_name


def update_universal_type_map(source_type, translated_type, map_file='data/java/type_resolution/universal_type_map_final.json'):
    """
    Update the universal type map with successful translations.
    If a source type is already recorded, do not overwrite it.

    Args:
        source_type (str): Original Java type
        translated_type (str): Translated Cangjie type
        map_file (str): Path to the universal type map JSON file
    """
    # Load existing map
    type_map = {}
    if os.path.exists(map_file):
        try:
            with open(map_file, 'r') as f:
                type_map = json.load(f)
        except (json.JSONDecodeError, IOError):
            type_map = {}

    # Only add if not already recorded
    if source_type not in type_map:
        type_map[source_type] = translated_type
        # Ensure directory exists
        os.makedirs(os.path.dirname(map_file), exist_ok=True)
        # Save updated map
        with open(map_file, 'w') as f:
            json.dump(type_map, f, indent=4)
    return type_map.get(source_type, translated_type)


def is_type_loadable(import_stmt, type_name, custom_classes=None):
    """
    Validates if a type can be loaded or used in the Cangjie type system
    by attempting to compile a test program using cjc.

    Args:
        import_stmt (str): The import statement needed to access the type, or empty if built-in
        type_name (str): The name of the type to validate
        custom_classes (list, optional): List of custom class names to treat as valid types

    Returns:
        tuple: (bool, str) indicating if the type can be loaded and an error message if applicable
    """
    if isinstance(type_name, str):
        if "#" in type_name:
            return False, 'invalid type name'

    type_name = type_name.strip() if type_name else ''
    import_stmt = import_stmt.strip() if import_stmt else ''
    custom_classes = custom_classes or []

    if import_stmt == '' and type_name == '':
        return False, 'no type translation has been provided'

    # Generate stub class definitions for custom types so cjc can resolve them
    custom_stubs = ''
    for simple_name in dedupe_preserve_order(
        (_cangjie_stub_name(cls) for cls in custom_classes),
    ):
        if not simple_name:
            continue
        # Cangjie doesn't support nested classes; use only the simple name.
        custom_stubs += f'class {simple_name} {{}}\n'

    # Generate Cangjie test program - simplified validation
    cangjie_program = f"""package test

{import_stmt}

{custom_stubs}
main(): Int64 {{
    let _test_val: {type_name}
    0
}}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.cj', delete=False, dir='/tmp') as f:
        f.write(cangjie_program)
        temp_file = f.name

    try:
        # Compile check using cjc (run in /tmp so main/test.cjo don't pollute project root)
        result = subprocess.run(
            ["cjc", temp_file],
            capture_output=True,
            timeout=60,
            cwd="/tmp",
        )

        if result.returncode != 0:
            error_output = result.stdout.decode('utf-8') if result.stdout else result.stderr.decode('utf-8') if result.stderr else "Unknown error"
            return False, f'Cangjie compilation error: {error_output}'

        return True, ''

    except subprocess.CalledProcessError as e:
        error_output = e.stdout.decode('utf-8') if e.stdout else e.stderr.decode('utf-8') if e.stderr else "Unknown error"
        return False, f'Cangjie compilation error: {error_output}'

    except FileNotFoundError:
        return False, 'cjc compiler not found - please ensure Cangjie SDK is installed'

    except subprocess.TimeoutExpired:
        return False, 'Cangjie compilation timed out'

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main(args):
    log_path = init_type_resolution_log(args)

    # Load fixed type map from JSON (more accurate than old hardcoded JAVA_TO_CANGJIE_PRIMITIVES)
    FIXED_TYPE_MAP = {}
    fixed_map_path = "data/java/type_resolution/fixed_type_map.json"
    if os.path.exists(fixed_map_path):
        with open(fixed_map_path, 'r') as f:
            FIXED_TYPE_MAP = json.load(f)
    log_detail(log_path, 'CONFIG', f'Loaded {len(FIXED_TYPE_MAP)} entries from fixed_type_map.json')

    # Load universal type map as cache to avoid re-translating already-seen types
    UNIVERSAL_TYPE_MAP = {}
    universal_map_path = "data/java/type_resolution/universal_type_map_final.json"
    if os.path.exists(universal_map_path):
        with open(universal_map_path, 'r') as f:
            UNIVERSAL_TYPE_MAP = json.load(f)
    log_detail(log_path, 'CONFIG', f'Loaded {len(UNIVERSAL_TYPE_MAP)} entries from universal_type_map_final.json as cache')

    # Initialize Progressive Knowledge Base (if enabled)
    kb = None
    if getattr(args, 'use_progressive_kb', 'false') == 'true':
        try:
            kb = get_progressive_kb()
            kb.ensure_dirs()
            log_detail(log_path, 'CONFIG', f'Progressive KB enabled: {kb.pair_count} pairs, {kb.type_mapping_count} type mappings')
        except Exception as e:
            log_detail(log_path, 'CONFIG', f'Progressive KB init failed (will proceed without): {e}')
            kb = None

    # Initialize Generics Rule Library (always loaded; lightweight memoization)
    generics_lib = None
    try:
        generics_lib = get_generics_rule_lib()
        log_detail(log_path, 'CONFIG', f'Generics Rule Lib loaded: {generics_lib.rule_count} rules, {generics_lib.container_count} container mappings')
    except Exception as e:
        log_detail(log_path, 'CONFIG', f'Generics Rule Lib init failed (will proceed without): {e}')
        generics_lib = None

    model_info = yaml.safe_load(open('configs/model_configs.yaml', 'r'))['models']
    args.schema_dir = f'data/java/schemas{args.suffix}/{args.model_name}/{args.temperature}/{args.project_name}'
    model = Model(model_info=model_info[args.model_name])
    include_tests = _should_include_test_sources(args)
    total_types = count_pending_type_translations(args.schema_dir, include_tests=include_tests)
    processed_types = 0

    # Get custom types from schema files and persist to JSON
    schema_filter = lambda schema_file: include_tests or not _is_test_schema_name(schema_file)
    custom_types = get_custom_types(args.schema_dir, schema_filter=schema_filter)
    custom_type_map = get_custom_type_translation_map(args.schema_dir, schema_filter=schema_filter)
    save_custom_types(args.project_name, custom_types)
    log_detail(log_path, 'CUSTOM TYPES', f'Loaded {len(custom_types)} custom types')

    for schema_file in os.listdir(args.schema_dir):
        if _is_test_schema_name(schema_file) and not include_tests:
            continue

        data = {}
        with open(f'{args.schema_dir}/{schema_file}', 'r') as f:
            data = json.load(f)

        for class_ in data['classes']:
            for fragment_type in ['field', 'method']:
                for fragment in data['classes'][class_][f'{fragment_type}s']:
                    fragment_body = '\n'.join(data['classes'][class_][f'{fragment_type}s'][fragment]['body'])
                    fragment_body = '    ' + fragment_body
                    type_variations = {'types': 'FIELD TYPE', 'return_types': 'RETURN TYPE', 'parameters': 'PARAMETER TYPE', 'body_types': 'METHOD BODY TYPE'}

                    for type_variation in type_variations:

                        if fragment_type == 'field' and type_variation != 'types':
                            continue
                        elif fragment_type == 'method' and type_variation == 'types':
                            continue

                        interaction_history = []
                        feedback = ''
                        budget = args.budget
                        i = 0
                        while i < len(data['classes'][class_][f'{fragment_type}s'][fragment][type_variation]):

                            type_ = data['classes'][class_][f'{fragment_type}s'][fragment][type_variation][i]
                            type_identifier = type_ if type_variation in ['types', 'return_types', 'body_types'] else f'{type_["modifier"]}|{type_["type"]}|{type_["name"]}'

                            if data['classes'][class_][f'{fragment_type}s'][fragment]['type_translations'][type_variation][type_identifier]['translated']:
                                i += 1
                                interaction_history = []
                                feedback = ''
                                budget = args.budget
                                continue

                            source_type = type_ if type_variation in ['types', 'return_types', 'body_types'] else type_["type"]

                            if budget == 0:
                                fallback_type = fallback_type_for(source_type)
                                # Determine if the fallback produced a meaningful mapping (not just 'Any')
                                fallback_is_meaningful = fallback_type != 'Any'
                                result = Result()
                                result.attempted = True
                                result.identifier = type_identifier
                                result.translated = True
                                result.type_variation = type_variation
                                result.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                result.source_type = source_type
                                result.translated_target_type = fallback_type
                                result.feedback = feedback
                                fallback_type = update_universal_type_map(source_type, fallback_type)
                                result.translated_target_type = fallback_type
                                append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                save_results(data, args.schema_dir, schema_file)
                                processed_types += 1
                                if fallback_is_meaningful:
                                    terminal_type_status(processed_types, total_types, source_type, fallback_type, True, 'rule_lib:static_map')
                                    log_detail(log_path, f'PASS rule_lib:static_map {source_type}', f'{source_type} -> {fallback_type}')
                                else:
                                    terminal_type_status(processed_types, total_types, source_type, fallback_type, False, 'fallback:budget_exhausted')
                                    log_detail(log_path, f'FALLBACK budget_exhausted {source_type}', feedback)
                                i += 1
                                interaction_history = []
                                feedback = ''
                                budget = args.budget
                                continue

                            if interaction_history == []:
                                initial_interaction = Interaction(role='system', content='You are a helpful assistant.')
                                interaction_history.append(initial_interaction)

                            result = Result()
                            result.attempted = True
                            result.identifier = type_identifier
                            result.translated = False
                            result.type_variation = type_variation
                            result.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            result.source_type = source_type

                            # Check if it's a known fixed type, custom type, or already cached in universal map
                            if source_type in custom_types or source_type in FIXED_TYPE_MAP or source_type in UNIVERSAL_TYPE_MAP:
                                result.translated = True
                                if source_type in UNIVERSAL_TYPE_MAP:
                                    result.translated_target_type = UNIVERSAL_TYPE_MAP[source_type]
                                elif source_type in FIXED_TYPE_MAP:
                                    result.translated_target_type = FIXED_TYPE_MAP.get(source_type)
                                else:
                                    result.translated_target_type = custom_type_map.get(source_type, source_type)
                                # Record successful translation
                                result.translated_target_type = update_universal_type_map(source_type, result.translated_target_type)
                                append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                i += 1
                                interaction_history = []
                                feedback = ''
                                budget = args.budget

                                save_results(data, args.schema_dir, schema_file)
                                processed_types += 1
                                if source_type in UNIVERSAL_TYPE_MAP:
                                    reason = 'cached'
                                elif source_type in FIXED_TYPE_MAP:
                                    reason = 'fixed_map'
                                else:
                                    reason = 'custom_type'
                                terminal_type_status(processed_types, total_types, source_type, result.translated_target_type, True, reason)
                                log_detail(log_path, f'PASS {reason} {source_type}', f'{source_type} -> {result.translated_target_type}')

                                continue

                            # --- Progressive KB: check type mapping first (skip LLM if known) ---
                            kb_context = ""
                            if kb is not None:
                                kb_mapping = kb.get_type_mapping(source_type)
                                if kb_mapping and kb_mapping.verified:
                                    # Direct cache hit — no LLM call needed
                                    result.translated = True
                                    result.translated_target_type = kb_mapping.cangjie_type
                                    result.imports = '\n'.join(kb_mapping.imports) if kb_mapping.imports else None
                                    result.translated_target_type = update_universal_type_map(source_type, result.translated_target_type)
                                    append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                    i += 1
                                    interaction_history = []
                                    feedback = ''
                                    budget = args.budget
                                    save_results(data, args.schema_dir, schema_file)
                                    processed_types += 1
                                    terminal_type_status(processed_types, total_types, source_type, result.translated_target_type, True, 'progressive_kb_cache')
                                    log_detail(log_path, f'PASS progressive_kb_cache {source_type}', f'{source_type} -> {result.translated_target_type}')
                                    continue

                                # Retrieve few-shot examples for this type's context
                                kb_type_examples = kb.retrieve(
                                    java_code=fragment_body,
                                    java_types=[source_type],
                                    top_k=2,
                                )
                                if kb_type_examples:
                                    kb_context = kb.format_few_shot_prompt(kb_type_examples, max_examples=2)
                                    log_detail(log_path, f'KB FEW-SHOT {source_type}', f'Retrieved {len(kb_type_examples)} examples')

                                # Also inject type mapping context for related types
                                kb_type_ctx = kb.format_type_context([source_type])
                                if kb_type_ctx:
                                    kb_context = (kb_context + "\n\n" + kb_type_ctx).strip()

                            # --- Generics Rule Lib: inject matching rules as context ---
                            generics_context = ""
                            if generics_lib is not None and '<' in source_type:
                                generics_rules = generics_lib.match_rules_for_type(source_type, top_k=2)
                                if generics_rules:
                                    generics_context = generics_lib.format_rule_prompt(generics_rules, max_rules=2)
                                    log_detail(log_path, f'GENERICS RULE {source_type}', f'Matched {len(generics_rules)} rules: {[r["id"] for r in generics_rules]}')

                            # Skip LLM translation if use_llm is false — only fixed_type_map and custom types are used
                            if args.use_llm == 'false':
                                fallback_type = fallback_type_for(source_type)
                                fallback_is_meaningful = fallback_type != 'Any'
                                result.translated = True
                                result.translated_target_type = fallback_type
                                result.feedback = 'LLM translation disabled and no fixed/custom mapping was found'
                                fallback_type = update_universal_type_map(source_type, fallback_type)
                                result.translated_target_type = fallback_type
                                append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                save_results(data, args.schema_dir, schema_file)
                                processed_types += 1
                                if fallback_is_meaningful:
                                    terminal_type_status(processed_types, total_types, source_type, fallback_type, True, 'rule_lib:static_map')
                                    log_detail(log_path, f'PASS rule_lib:static_map {source_type}', f'{source_type} -> {fallback_type}')
                                else:
                                    terminal_type_status(processed_types, total_types, source_type, fallback_type, False, 'fallback:llm_disabled')
                                    log_detail(log_path, f'FALLBACK llm_disabled {source_type}', result.feedback)
                                i += 1
                                interaction_history = []
                                feedback = ''
                                budget = args.budget
                                continue

                            source_type_description = get_source_type_description(source_type)

                            # RAG context injection for type resolution (only when both use_llm and use_rag are true)
                            rag_context = ""
                            if args.use_rag == 'true' and args.use_llm == 'true':
                                try:
                                    with open(log_path, 'a') as log_file, contextlib.redirect_stdout(log_file):
                                        rag_engine = get_rag_engine()
                                        rag_ctx = rag_engine.inject_type_context(source_type)
                                    if rag_ctx:
                                        rag_context = rag_ctx
                                except Exception as e:
                                    log_detail(log_path, f'RAG WARNING {source_type}', f'Type RAG injection failed: {e}')

                            prompt_generator = TypePromptGenerator(
                                fragment_body,
                                fragment_type,
                                type_,
                                source_type_description,
                                type_variations[type_variation],
                                args.prompt_type,
                                args.source_language,
                                args.target_language,
                                feedback
                            )
                            prompt = prompt_generator.generate_prompt()
                            # Construct final prompt: Generics rules + KB examples + RAG docs + prompt
                            # Generics mapping rules (structural patterns) go first
                            # KB few-shot (real examples) goes before RAG docs (descriptions)
                            context_parts = []
                            if generics_context:
                                context_parts.append(generics_context)
                            if kb_context:
                                context_parts.append(kb_context)
                            if rag_context:
                                context_parts.append(rag_context)
                            if context_parts:
                                prompt = "\n\n".join(context_parts) + "\n\n" + prompt

                            interaction = Interaction(role='user', content=prompt)
                            interaction_history.append(interaction)

                            log_detail(log_path, f'PROMPT {source_type}', prompt)

                            messages = model.get_messages(interaction_history)
                            with open(log_path, 'a') as log_file, contextlib.redirect_stdout(log_file):
                                status, generation = model.prompt_model(messages)

                            result.generation = generation
                            result.prompt = prompt
                            append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                            save_results(data, args.schema_dir, schema_file)

                            if not status:
                                fallback_type = fallback_type_for(source_type)
                                fallback_is_meaningful = fallback_type != 'Any'
                                result.translated = True
                                result.translated_target_type = fallback_type
                                result.feedback = generation
                                fallback_type = update_universal_type_map(source_type, fallback_type)
                                result.translated_target_type = fallback_type
                                append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                save_results(data, args.schema_dir, schema_file)
                                processed_types += 1
                                if fallback_is_meaningful:
                                    terminal_type_status(processed_types, total_types, source_type, fallback_type, True, 'rule_lib:static_map')
                                    log_detail(log_path, f'PASS rule_lib:static_map {source_type}', f'{source_type} -> {fallback_type}')
                                else:
                                    terminal_type_status(processed_types, total_types, source_type, fallback_type, False, 'fallback:model_error')
                                    log_detail(log_path, f'FALLBACK model_error {source_type}', generation)
                                i += 1
                                interaction_history = []
                                feedback = ''
                                budget = args.budget
                                continue

                            interaction = Interaction(role='system', content=generation)
                            interaction_history.append(interaction)
                            log_detail(log_path, f'GENERATION {source_type}', generation)

                            try:
                                imports, translation, reasoning = Parser().parse_response(generation)
                            except BaseException:
                                feedback = 'Your response did not follow the RESPONSE FORMAT guidelines. Make sure you follow the RESPONSE FORMAT in your new response.'
                                log_detail(log_path, f'PARSE ERROR {source_type}', feedback)
                                budget -= 1
                                continue

                            if imports is None and translation is None and reasoning is None:
                                feedback = 'Your response did not follow the RESPONSE FORMAT guidelines. Make sure you follow the RESPONSE FORMAT in your new response.'
                                log_detail(log_path, f'PARSE ERROR {source_type}', feedback)
                                budget -= 1
                                continue

                            # --- IMPORTS fallback logic ---
                            # If LLM omitted the CANGJIE IMPORTS block (imports is None):
                            #   - For built-in types: accept as empty string (no imports needed)
                            #   - For non-built-in types: add feedback asking to re-provide with imports
                            if imports is None and translation is not None:
                                base_type = _strip_generic_params(translation)
                                if base_type in CANGJIE_BUILTIN_TYPES:
                                    # Built-in type — no imports actually needed
                                    imports = ''
                                    log_detail(log_path, f'IMPORTS INFERENCE {source_type}',
                                               f'LLM omitted IMPORTS block, but {translation} is a built-in type — treating as no imports needed')
                                else:
                                    # Non-built-in type — LLM must provide imports
                                    feedback = (
                                        f'Your translation "{translation}" may require import statements in Cangjie, '
                                        f'but you omitted the CANGJIE IMPORTS section. '
                                        f'Please provide your response again with the CANGJIE IMPORTS section filled in. '
                                        f'Every non-empty import line must start with "import ".'
                                    )
                                    log_detail(log_path, f'IMPORTS MISSING {source_type}', feedback)
                                    budget -= 1
                                    continue

                            if isinstance(translation, str):
                                if "#" in translation:
                                    translation = translation.split('#', 1)[0].strip()

                            # Validate type using Cangjie compilation
                            validation_result, feedback = is_type_loadable(imports or '', translation, custom_classes=custom_types)
                            if not validation_result:
                                log_detail(log_path, f'CJC VALIDATION FAILED {source_type}', feedback)
                                budget -= 1
                                continue

                            # Type validation passes
                            result.translated = True
                            result.imports = imports
                            result.translated_target_type = translation
                            result.reasoning = reasoning

                            # Record successful translation
                            translation = update_universal_type_map(source_type, translation)
                            result.translated_target_type = translation
                            log_detail(
                                log_path,
                                f'PASS llm {source_type}',
                                f'IMPORTS:\n{imports}\n\nTRANSLATION:\n{translation}\n\nREASONING:\n{reasoning}',
                            )

                            # --- Progressive KB: store successful type mapping ---
                            if kb is not None:
                                try:
                                    # Convert imports string to list, filtering out empty lines
                                    imports_list = [line for line in imports.split('\n') if line.strip()] if imports else []
                                    kb.add_type_mapping(
                                        java_type=source_type,
                                        cangjie_type=translation,
                                        imports=imports_list,
                                        source='llm',
                                        verified=True,
                                    )
                                except Exception as e:
                                    log_detail(log_path, f'KB WARNING {source_type}', f'Failed to store type mapping: {e}')

                            append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                            i += 1
                            interaction_history = []
                            feedback = ''
                            budget = args.budget

                            save_results(data, args.schema_dir, schema_file)
                            processed_types += 1
                            terminal_type_status(processed_types, total_types, source_type, translation, True, 'llm')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Translate java types to cangjie types')
    parser.add_argument('--project_name', type=str, dest='project_name', help='project name')
    parser.add_argument('--model_name', type=str, dest='model_name', help='model name to use for translation')
    parser.add_argument('--temperature', type=float, dest='temperature', help='temperature for generation')
    parser.add_argument('--suffix', type=str, dest='suffix', help='suffix for schema files')
    parser.add_argument('--debug', action='store_true', dest='debug', help='debug mode')
    parser.add_argument('--prompt_type', type=str, dest='prompt_type', help='prompt type')
    parser.add_argument('--source_language', type=str, dest='source_language', help='source language')
    parser.add_argument('--target_language', type=str, dest='target_language', help='target language')
    parser.add_argument('--budget', type=int, dest='budget', help='budget for each type translation')
    parser.add_argument('--use_llm', type=str, default='true', help='Enable LLM translation for unknown types (true/false). If false, only fixed_type_map and custom types are used.')
    parser.add_argument('--use_rag', type=str, default='false', help='Enable RAG context injection for type resolution (true/false). Only takes effect when use_llm is also true.')
    parser.add_argument('--use_progressive_kb', type=str, default='false', help='Enable Progressive Knowledge Base for type resolution (true/false). Provides few-shot examples from verified translations before LLM calls.')
    parser.add_argument('--translate_tests', type=str, default='false', help='Include src/test Java schemas in type translation (true/false).')
    args = parser.parse_args()
    main(args)
