import argparse
import json
import os
import re
from datetime import datetime

import yaml
from openai import OpenAI

from src.java.progressive_kb import get_progressive_kb
from src.java.generics_rule_lib import get_generics_rule_lib
from src.java.type_resolution.interface_shim import InterfaceShimRegistry
from src.java.type_resolution.type_expression import (
    build_default_type_map,
    get_cangjie_type as deterministic_get_cangjie_type,
    is_known_type_expression,
    is_type_parameter,
)
from src.java.utils.get_custom_types import (
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
    """Backward-compatible wrapper around the shared type-parameter detector."""
    return is_type_parameter(source_type)


def _has_balanced_generic_brackets(source_type):
    """Return True when the type string contains a balanced generic argument list."""
    if not source_type or '<' not in source_type or '>' not in source_type:
        return False

    depth = 0
    saw_generic = False
    for char in str(source_type):
        if char == '<':
            depth += 1
            saw_generic = True
        elif char == '>':
            depth -= 1
            if depth < 0:
                return False
    return saw_generic and depth == 0


def _generic_complexity_reason(source_type):
    """Classify generic syntax that should not be swallowed by interface shims."""
    if not _has_balanced_generic_brackets(source_type):
        return ''

    text = str(source_type).strip()
    base = text.split('<', 1)[0].split('.')[-1].strip()
    if re.search(r'<[^>]*\?[^>]*<|<[^>]*<[^>]*\?|\w+\s*<\s*\w+\s*<\s*\?', text):
        return 'nested_wildcard'
    if re.search(r'\?\s+extends\b', text):
        return 'upper_bounded_wildcard'
    if re.search(r'\?\s+super\b', text):
        return 'lower_bounded_wildcard'
    if re.search(r'<\s*\?\s*>', text):
        return 'unbounded_wildcard'
    if base == 'Class':
        return 'type_token'
    if base in {'Stream', 'Collector', 'Collectors', 'CompletableFuture'}:
        return 'semantic_generic_api'
    if re.search(r'\bextends\b[^<>&]*&', text):
        return 'intersection_bound'
    if re.search(r'\b([A-Z]\w*)\s+extends\s+Comparable\s*<\s*\1\s*>', text):
        return 'recursive_bound'
    return ''


def _match_generics_rules(generics_lib, source_type, log_path):
    """Return (matched_rules, reason) for unresolved generic types."""
    if not generics_lib or not _has_balanced_generic_brackets(source_type):
        return [], ''

    generics_rules = generics_lib.match_rules_for_type(source_type, top_k=2)
    complexity_reason = _generic_complexity_reason(source_type)
    if not generics_rules and complexity_reason:
        generics_lib._ensure_loaded()
        reason_to_subcategories = {
            'upper_bounded_wildcard': {'upper_bounded_wildcard'},
            'lower_bounded_wildcard': {'lower_bounded_wildcard'},
            'unbounded_wildcard': {'unbounded_wildcard'},
            'nested_wildcard': {'nested_wildcard'},
            'intersection_bound': {'multi_constraint'},
            'recursive_bound': {'recursive_constraint', 'recursive_bound'},
        }
        wanted = reason_to_subcategories.get(complexity_reason, set())
        generics_rules = [
            rule for rule in generics_lib.rules
            if rule.get('subcategory') in wanted
        ][:2]

    if generics_rules:
        log_detail(
            log_path,
            f'GENERICS RULE {source_type}',
            f'Matched {len(generics_rules)} rules: {[r["id"] for r in generics_rules]}',
        )
    return generics_rules, complexity_reason


def _strip_json_fence(text):
    stripped = (text or '').strip()
    if stripped.startswith('```'):
        first_newline = stripped.find('\n')
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        if stripped.endswith('```'):
            stripped = stripped[:-3].rstrip()
    return stripped


def _build_complex_generic_prompt(
    source_type,
    fragment_body,
    type_variation,
    type_info,
    generics_rules,
    generic_reason,
    generics_lib,
):
    rule_context = ''
    if generics_rules and generics_lib:
        rule_context = generics_lib.format_rule_prompt(generics_rules, max_rules=3)

    type_location = type_variation
    if isinstance(type_info, dict):
        name = type_info.get('name', '')
        modifier = type_info.get('modifier', '')
        if name or modifier:
            type_location = f'{type_variation}: {modifier} {name}'.strip()

    return f"""You are translating one Java type expression to Cangjie for a Java-to-Cangjie type-resolution pipeline.

Return ONLY valid JSON, no markdown.

JSON schema:
{{
  "target_type": "the Cangjie type expression to write into the schema",
  "reasoning": "brief reason",
  "imports": "optional imports, empty string if none"
}}

Source Java type:
{source_type}

Type location:
{type_location}

Complex generic reason:
{generic_reason or "matched_generics_rule"}

Java fragment context:
```java
{fragment_body}
```

{rule_context}

Instructions:
- Apply the matched generics rules when they fit.
- Prefer Cangjie type syntax, not Java syntax.
- For Java wildcard upper bounds such as List<? extends Number>, introduce a type variable when needed and preserve the bound in the returned type expression if it is representable.
- For Java wildcard lower bounds such as List<? super Integer>, use the Cangjie projection form shown by the rules when applicable.
- If the exact Java construct requires a method/class-level where clause and cannot be represented as a plain inline type, return the closest usable Cangjie type expression and explain the missing declaration-level constraint in reasoning.
- Do not return a full method, field, or class.
"""


def _translate_complex_generic_with_llm(
    source_type,
    fragment_body,
    type_variation,
    type_info,
    generics_rules,
    generic_reason,
    generics_lib,
    model_client,
    model_cfg,
    args,
    log_path,
):
    if model_client is None or model_cfg is None:
        return None, 'model_not_initialized'

    prompt = _build_complex_generic_prompt(
        source_type=source_type,
        fragment_body=fragment_body,
        type_variation=type_variation,
        type_info=type_info,
        generics_rules=generics_rules,
        generic_reason=generic_reason,
        generics_lib=generics_lib,
    )
    messages = [
        {
            'role': 'system',
            'content': 'You are a Java to Cangjie type translation expert. You output only valid JSON.',
        },
        {'role': 'user', 'content': prompt},
    ]

    kwargs = {
        'model': model_cfg['model_id'],
        'messages': messages,
        'max_tokens': min(1024, model_cfg.get('max_new_tokens', 1024)),
        'temperature': getattr(args, 'temperature', 0.0),
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
    }
    if args.model_name in {'gpt-4o-2024-11-20', 'gpt-4o', 'gpt-4'}:
        kwargs['response_format'] = {'type': 'json_object'}

    try:
        completion = model_client.chat.completions.create(**kwargs)
        generation = completion.choices[0].message.content or ''
    except Exception as exc:
        return None, f'llm_request_failed: {exc}'

    log_detail(log_path, f'LLM COMPLEX GENERIC PROMPT {source_type}', prompt)
    log_detail(log_path, f'LLM COMPLEX GENERIC GENERATION {source_type}', generation)

    try:
        parsed = json.loads(_strip_json_fence(generation))
    except json.JSONDecodeError as exc:
        return None, f'llm_invalid_json: {exc}'

    target_type = str(parsed.get('target_type') or parsed.get('type') or '').strip()
    if not target_type:
        return None, 'llm_empty_target_type'

    return {
        'target_type': target_type,
        'reasoning': str(parsed.get('reasoning') or '').strip(),
        'imports': str(parsed.get('imports') or '').strip(),
        'generation': generation,
        'prompt': prompt,
    }, ''


def fallback_type_for(source_type):
    """Determine a fallback Cangjie type for a Java type when no other mapping is available.

    Deterministic type-expression translation uses the java.base map.
    Generics language mechanisms that cannot be reduced to a concrete type
    expression still fall back to Any when the LLM path is off or exhausted.
    """
    if not source_type:
        return 'Any'

    stripped = source_type.strip()
    static_type_map = build_default_type_map()
    if not is_known_type_expression(stripped, static_type_map):
        return 'Any'
    translated = deterministic_get_cangjie_type(stripped, static_type_map)
    return translated or 'Any'

def main(args):
    log_path = init_type_resolution_log(args)

    STATIC_TYPE_MAP = build_default_type_map()
    log_detail(log_path, 'CONFIG', f'Loaded {len(STATIC_TYPE_MAP)} deterministic type entries')

    model_client = None
    model_cfg = None
    try:
        model_info = yaml.safe_load(open("configs/model_configs.yaml", "r"))["models"]
        model_cfg = model_info.get(args.model_name)
        if model_cfg:
            model_client = OpenAI(
                **{
                    k: v
                    for k, v in model_cfg.items()
                    if k in ["api_key", "base_url", "default_headers"]
                }
            )
            log_detail(log_path, 'CONFIG', f'LLM enabled for complex generics: {args.model_name}')
        else:
            log_detail(log_path, 'CONFIG', f'LLM config missing for model: {args.model_name}')
    except Exception as e:
        log_detail(log_path, 'CONFIG', f'LLM init failed for complex generics: {e}')

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

    args.schema_dir = f'data/java/schemas{args.suffix}/{args.model_name}/{args.temperature}/{args.project_name}'
    include_tests = _should_include_test_sources(args)
    total_types = count_pending_type_translations(args.schema_dir, include_tests=include_tests)
    processed_types = 0

    # Get custom types from schema files and persist to JSON
    schema_filter = lambda schema_file: include_tests or not _is_test_schema_name(schema_file)
    custom_types = get_custom_types(args.schema_dir, schema_filter=schema_filter)
    custom_type_map = get_custom_type_translation_map(args.schema_dir, schema_filter=schema_filter)
    save_custom_types(args.project_name, custom_types)
    log_detail(log_path, 'CUSTOM TYPES', f'Loaded {len(custom_types)} custom types')

    shim_registry = InterfaceShimRegistry(
        args.project_name,
        cjpm_name=args.project_name.replace('-', '_'),
        deterministic_type_map={**STATIC_TYPE_MAP, **custom_type_map},
    )

    for schema_file in os.listdir(args.schema_dir):
        if _is_test_schema_name(schema_file) and not include_tests:
            continue

        data = {}
        with open(f'{args.schema_dir}/{schema_file}', 'r') as f:
            data = json.load(f)
        import_map = data.get('import_map', {}) if isinstance(data.get('import_map', {}), dict) else {}
        shim_registry.set_import_map(import_map)
        schema_type_map = {**STATIC_TYPE_MAP, **custom_type_map}
        for short_name, full_name in import_map.items():
            mapped = deterministic_get_cangjie_type(full_name, schema_type_map)
            if is_known_type_expression(full_name, schema_type_map):
                schema_type_map.setdefault(short_name, mapped)

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

                        i = 0
                        while i < len(data['classes'][class_][f'{fragment_type}s'][fragment][type_variation]):

                            type_ = data['classes'][class_][f'{fragment_type}s'][fragment][type_variation][i]
                            type_identifier = type_ if type_variation in ['types', 'return_types', 'body_types'] else f'{type_["modifier"]}|{type_["type"]}|{type_["name"]}'

                            if data['classes'][class_][f'{fragment_type}s'][fragment]['type_translations'][type_variation][type_identifier]['translated']:
                                i += 1
                                continue

                            source_type = type_ if type_variation in ['types', 'return_types', 'body_types'] else type_["type"]

                            result = Result()
                            result.attempted = True
                            result.identifier = type_identifier
                            result.translated = False
                            result.type_variation = type_variation
                            result.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            result.source_type = source_type

                            generics_rules, generic_reason = _match_generics_rules(
                                generics_lib,
                                source_type,
                                log_path,
                            )
                            unresolved_generic = _has_balanced_generic_brackets(source_type)
                            complex_generic = bool(generic_reason or generics_rules)

                            deterministic_type = deterministic_get_cangjie_type(source_type, schema_type_map)
                            has_deterministic_type = is_known_type_expression(source_type, schema_type_map)

                            # Check if it's a known fixed/java.base type, custom type,
                            # or a deterministic expression such as List<String> or int[].
                            if (
                                source_type in custom_types
                                or source_type in STATIC_TYPE_MAP
                                or has_deterministic_type
                            ):
                                result.translated = True
                                if source_type in STATIC_TYPE_MAP or has_deterministic_type:
                                    result.translated_target_type = deterministic_type
                                else:
                                    result.translated_target_type = custom_type_map.get(source_type, source_type)
                                append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                i += 1

                                save_results(data, args.schema_dir, schema_file)
                                processed_types += 1
                                if source_type in STATIC_TYPE_MAP:
                                    reason = 'java_base_map'
                                elif has_deterministic_type:
                                    reason = 'deterministic_type_expression'
                                else:
                                    reason = 'custom_type'
                                terminal_type_status(processed_types, total_types, source_type, result.translated_target_type, True, reason)
                                log_detail(log_path, f'PASS {reason} {source_type}', f'{source_type} -> {result.translated_target_type}')

                                continue

                            if '|' in source_type or '&' in source_type:
                                result.translated = True
                                result.translated_target_type = 'Any'
                                result.feedback = 'Unsupported Java type expression; not a concrete type name for interface shim generation'
                                append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                save_results(data, args.schema_dir, schema_file)
                                processed_types += 1
                                terminal_type_status(processed_types, total_types, source_type, 'Any', False, 'fallback:unsupported_type_expression')
                                log_detail(log_path, f'FALLBACK unsupported_type_expression {source_type}', result.feedback)
                                i += 1
                                continue

                            # Unresolved generic expressions should not be swallowed by
                            # interface shims. Concrete generic containers have already
                            # been handled by deterministic_type_expression above; the
                            # remaining generic cases are either semantic APIs, wildcard
                            # forms, or unknown generic bases that need rule/LLM handling.
                            if unresolved_generic:
                                log_detail(
                                    log_path,
                                    f'SKIP SHIM generic {source_type}',
                                    f'reason={generic_reason or ("generics_rule" if generics_rules else "unresolved_generic")}',
                                )

                                if generics_rules or generic_reason:
                                    llm_result, llm_error = _translate_complex_generic_with_llm(
                                        source_type=source_type,
                                        fragment_body=fragment_body,
                                        type_variation=type_variation,
                                        type_info=type_,
                                        generics_rules=generics_rules,
                                        generic_reason=generic_reason,
                                        generics_lib=generics_lib,
                                        model_client=model_client,
                                        model_cfg=model_cfg,
                                        args=args,
                                        log_path=log_path,
                                    )
                                    if llm_result:
                                        result.translated = True
                                        result.translated_target_type = llm_result['target_type']
                                        result.reasoning = llm_result['reasoning']
                                        result.imports = llm_result['imports']
                                        result.generation = llm_result['generation']
                                        result.prompt = llm_result['prompt']
                                        append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                        i += 1
                                        save_results(data, args.schema_dir, schema_file)
                                        processed_types += 1
                                        terminal_type_status(processed_types, total_types, source_type, result.translated_target_type, True, 'llm:complex_generic')
                                        log_detail(log_path, f'PASS llm:complex_generic {source_type}', f'{source_type} -> {result.translated_target_type}')
                                        continue
                                    log_detail(log_path, f'LLM COMPLEX GENERIC FAILED {source_type}', llm_error)

                            if not unresolved_generic:
                                shim_type = shim_registry.translate_or_create(
                                    source_type,
                                    fragment_body=fragment_body,
                                    type_variation=type_variation,
                                    type_info=type_,
                                )
                                if shim_type:
                                    result.translated = True
                                    result.imports = shim_registry.import_line
                                    result.translated_target_type = shim_type
                                    result.reasoning = 'generated_interface_shim'
                                    append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                    i += 1

                                    save_results(data, args.schema_dir, schema_file)
                                    processed_types += 1
                                    terminal_type_status(processed_types, total_types, source_type, shim_type, True, 'generated_interface_shim')
                                    log_detail(log_path, f'PASS generated_interface_shim {source_type}', f'{source_type} -> {shim_type}')
                                    continue

                            # --- Progressive KB: check verified type mapping cache ---
                            if kb is not None:
                                kb_mapping = kb.get_type_mapping(source_type)
                                if kb_mapping and kb_mapping.verified:
                                    result.translated = True
                                    result.translated_target_type = kb_mapping.cangjie_type
                                    result.imports = '\n'.join(kb_mapping.imports) if kb_mapping.imports else None
                                    append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                                    i += 1
                                    save_results(data, args.schema_dir, schema_file)
                                    processed_types += 1
                                    terminal_type_status(processed_types, total_types, source_type, result.translated_target_type, True, 'progressive_kb_cache')
                                    log_detail(log_path, f'PASS progressive_kb_cache {source_type}', f'{source_type} -> {result.translated_target_type}')
                                    continue

                            fallback_type = fallback_type_for(source_type)
                            fallback_is_meaningful = fallback_type != 'Any'
                            result.translated = True
                            result.translated_target_type = fallback_type
                            if unresolved_generic:
                                result.feedback = f'Unresolved generic type; no dynamic translation path is enabled. reason={generic_reason or "unresolved_generic"}'
                            else:
                                result.feedback = 'No deterministic, Progressive KB, or interface shim mapping was found'
                            append_result(data, class_, fragment_type, fragment, type_variation, type_, result)
                            i += 1
                            save_results(data, args.schema_dir, schema_file)
                            processed_types += 1
                            if fallback_is_meaningful:
                                terminal_type_status(processed_types, total_types, source_type, fallback_type, True, 'rule_lib:static_map')
                                log_detail(log_path, f'PASS rule_lib:static_map {source_type}', f'{source_type} -> {fallback_type}')
                            else:
                                terminal_type_status(processed_types, total_types, source_type, fallback_type, False, 'fallback:no_type_mapping')
                                log_detail(log_path, f'FALLBACK no_type_mapping {source_type}', result.feedback)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Translate java types to cangjie types')
    parser.add_argument('--project_name', type=str, dest='project_name', help='project name')
    parser.add_argument('--model_name', type=str, dest='model_name', help='model name to use for translation')
    parser.add_argument('--temperature', type=float, dest='temperature', help='temperature for generation')
    parser.add_argument('--suffix', type=str, dest='suffix', help='suffix for schema files')
    parser.add_argument('--debug', action='store_true', dest='debug', help='debug mode')
    parser.add_argument('--use_progressive_kb', type=str, default='false', help='Enable Progressive Knowledge Base type mapping cache (true/false).')
    parser.add_argument('--translate_tests', type=str, default='false', help='Include src/test Java schemas in type translation (true/false).')
    args = parser.parse_args()
    main(args)
