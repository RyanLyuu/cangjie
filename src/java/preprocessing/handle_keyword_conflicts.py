#!/usr/bin/env python3
"""
Handle Cangjie keyword conflicts in Java code using tree-sitter.
When Java identifiers conflict with Cangjie keywords (type, init, in, is, func, match),
append suffix to make them valid Cangjie identifiers.

Non-method identifiers (fields, params, locals, field accesses) -> '__' suffix
Method-related identifiers (declarations, invocations)         -> '_' suffix
JDK built-in references (System.in) and inherited fields       -> preserved unchanged
"""
import argparse
import os
import shutil

from src.java.preprocessing._shared import (
    load_parser, extract_text_by_bytes, _skip_dir,
    clean_target_dirs, pre_scan_project
)


# Cangjie keywords that can conflict with Java identifiers
CANGJIE_KEYWORDS = {
    'type', 'init', 'in', 'is','match', 'func', 'class', 'interface', 'struct',
    'enum', 'public', 'private', 'protected', 'internal', 'static', 'var',
    'let', 'import', 'package', 'return', 'if', 'else', 'for', 'while', 'match',
    'where', 'throws', 'try', 'catch', 'finally', 'override', 'abstract',
    'final', 'native', 'synchronized', 'transient', 'volatile',
}

# Keywords both Java and Cangjie reserve as keywords — no rename needed
SKIP_KEYWORDS = {
    'class', 'enum', 'interface', 'struct', 'import', 'package',
    'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'finally',
    'throws', 'override', 'abstract', 'final', 'native', 'synchronized',
    'transient', 'volatile', 'public', 'private', 'protected', 'internal',
    'static', 'var', 'let', 'where', 'main'
}

# The actual keywords that need renaming
ACTIVE_KEYWORDS = CANGJIE_KEYWORDS - SKIP_KEYWORDS  # {'type', 'init', 'in', 'is', 'func', 'match'}


# ---------------------------------------------------------------------------
# Phase 1: Pre-scan (delegates to _shared.pre_scan_project)
# ---------------------------------------------------------------------------

def pre_scan_project_keywords(output_dir, collect_methods=False):
    """Pre-scan collecting user classes and keyword declaration sites."""
    return pre_scan_project(output_dir, active_keywords=ACTIVE_KEYWORDS,
                            collect_method_decls=collect_methods)


# ---------------------------------------------------------------------------
# Phase 2: Context-aware renaming
# ---------------------------------------------------------------------------

def _get_enclosing_class_name(node, code):
    """Walk up the AST to find the nearest enclosing class name."""
    current = node.parent
    while current:
        if current.type in ('class_declaration', 'interface_declaration',
                            'enum_declaration', 'record_declaration'):
            name_node = current.child_by_field_name('name')
            if name_node:
                return extract_text_by_bytes(code, name_node.start_byte,
                                             name_node.end_byte)
        current = current.parent
    return None


def _get_identifier_context(node, code, user_classes, project_method_decls=None):
    """
    Determine the rename context for an identifier node.

    Returns (suffix, should_skip):
      suffix:      '__' for non-method, '_' for method
      should_skip: True if this is a JDK/external reference that must not change
    """
    parent = node.parent
    if parent is None:
        return ('__', False)

    pt = parent.type

    # --- Method / constructor declaration name -> '_' ------------------------
    if pt in ('method_declaration', 'constructor_declaration'):
        if parent.child_by_field_name('name') == node:
            return ('_', False)

    # --- Method invocation (call site) -> '_', with JDK-class guard ----------
    #     Also guards against external-library calls on lowercase variables
    #     (e.g. mac.init() where mac is javax.crypto.Mac, not project code)
    #     and static imports (e.g. is() from Hamcrest) by checking whether the
    #     method name is declared anywhere in the project.
    if pt == 'method_invocation':
        if parent.child_by_field_name('name') == node:
            obj = parent.child_by_field_name('object')
            if obj and _is_jdk_class_ref(obj, code, user_classes):
                return ('_', True)
            # No receiver (implicit this / static import): only rename if the
            # method is declared in the project (e.g. is() from Hamcrest
            # should not be renamed if no project class declares is()).
            if obj is None and project_method_decls is not None:
                name = extract_text_by_bytes(code, node.start_byte, node.end_byte)
                if name not in project_method_decls:
                    return ('_', True)
                return ('_', False)
            # Lowercase variable as receiver: likely an external library instance.
            # Only rename if the method is declared in the project.
            if (obj and obj.type == 'identifier'
                    and obj != parent.child_by_field_name('name')
                    and project_method_decls is not None):
                name = extract_text_by_bytes(code, node.start_byte, node.end_byte)
                if name not in project_method_decls:
                    return ('_', True)
            return ('_', False)

    # --- Field access (obj.field) -> '__', with JDK-class guard --------------
    if pt == 'field_access':
        if parent.child_by_field_name('field') == node:
            obj = parent.child_by_field_name('object')
            if obj and _is_jdk_class_ref(obj, code, user_classes):
                return ('__', True)
            # 'this' / 'super' -> defer to file_decls (inherited JDK field?)
            if obj and obj.type in ('this', 'super'):
                return ('__', None)
            return ('__', False)

    # --- Everything else (params, locals, standalones, etc.) -> handled
    #     at the call site via file_decls check.  We return a neutral default
    #     and the caller makes the final decision.
    return ('__', None)   # 'None' should_skip -> caller checks file_decls


def _is_jdk_class_ref(obj_node, code, user_classes):
    """
    Does *obj_node* refer to a JDK/external class (uppercase, not user-defined)?

    Walks method/field chains to find the root receiver.
    """
    obj = obj_node
    while obj.type == 'parenthesized_expression':
        obj = obj.children[1] if len(obj.children) > 1 else obj

    # Direct identifier: System.in
    if obj.type == 'identifier':
        text = extract_text_by_bytes(code, obj.start_byte, obj.end_byte)
        return text[0].isupper() and text not in user_classes

    # Scoped identifier: java.lang.System.in
    if obj.type == 'scoped_identifier':
        name = obj.child_by_field_name('name')
        if name:
            text = extract_text_by_bytes(code, name.start_byte, name.end_byte)
            return text[0].isupper() and text not in user_classes

    # Chain: Option.builder().type() — follow the chain root
    if obj.type == 'method_invocation':
        inner = obj.child_by_field_name('object')
        return _is_jdk_class_ref(inner, code, user_classes) if inner else False

    if obj.type == 'field_access':
        inner = obj.child_by_field_name('object')
        return _is_jdk_class_ref(inner, code, user_classes) if inner else False

    # 'this', 'super', variable -> not (necessarily) a JDK class
    return False


def find_identifier_conflicts(node, code, conflicts, user_classes, file_decls,
                              project_method_decls=None):
    """
    Recursively find all identifier nodes that need renaming.

    Appends (start_byte, end_byte, original_name, new_name) to *conflicts*.
    """
    nt = node.type

    if nt in ('identifier', 'type_identifier'):
        name = extract_text_by_bytes(code, node.start_byte, node.end_byte)
        if name in ACTIVE_KEYWORDS:
            suffix, should_skip = _get_identifier_context(node, code,
                                                         user_classes,
                                                         project_method_decls)
            # 'None' -> undecided; check if 'name' is declared in this file.
            # If not, it's an inherited/external ref (e.g. FilterInputStream.in).
            if should_skip is None:
                should_skip = name not in file_decls

            if not should_skip:
                conflicts.append((node.start_byte, node.end_byte,
                                  name, name + suffix))

    for child in node.children:
        find_identifier_conflicts(child, code, conflicts, user_classes,
                                  file_decls, project_method_decls)


def process_java_file(file_path, parser, user_classes, file_decls,
                      project_method_decls=None):
    """
    Parse one Java file, rename conflicting identifiers, write back.

    Returns True if the file was modified.
    """
    with open(file_path, 'rb') as f:
        code = f.read()

    tree = parser.parse(code)

    conflicts = []
    find_identifier_conflicts(tree.root_node, code, conflicts,
                              user_classes, file_decls.get(file_path, set()),
                              project_method_decls)

    if not conflicts:
        return False

    # Deduplicate by start_byte
    seen = set()
    unique = []
    for c in conflicts:
        if c[0] not in seen:
            seen.add(c[0])
            unique.append(c)
    conflicts = unique

    # Sort descending so edits don't shift positions
    conflicts.sort(key=lambda x: x[0], reverse=True)

    code_list = bytearray(code)
    for start, end, old_name, new_name in conflicts:
        if code_list[start:end].decode('utf-8') == old_name:
            code_list[start:end] = new_name.encode('utf-8')

    with open(file_path, 'wb') as f:
        f.write(code_list)

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args):
    input_dir = f"projects/java/automated_reduced_projects/{args.project}"
    output_dir = f"projects/java/keyword_handled/{args.project}"

    if not os.path.exists(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Copy directory tree
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    shutil.copytree(input_dir, output_dir)

    # Phase 1: Pre-scan (also collect project-wide method declarations for
    # active keywords, to avoid renaming external-library method calls like
    # mac.init() where mac is a JDK type instance)
    print("Pre-scanning project...")
    parser, user_classes, file_decls, project_method_decls = \
        pre_scan_project_keywords(output_dir, collect_methods=True)
    print(f"  User-defined classes: {len(user_classes)}")
    print(f"  Files with keyword declarations: "
          f"{sum(1 for v in file_decls.values() if v)}")
    print(f"  Project methods matching active keywords: "
          f"{sorted(project_method_decls) if project_method_decls else '(none)'}")

    # Phase 2: Process all Java files
    java_files = []
    for root, dirs, files in os.walk(output_dir):
        if _skip_dir(root):
            continue
        for fname in files:
            if fname.endswith('.java'):
                java_files.append(os.path.join(root, fname))

    print(f"Processing {len(java_files)} Java files...")

    total_modified = 0
    for java_file in java_files:
        rel_path = os.path.relpath(java_file, output_dir)
        if process_java_file(java_file, parser, user_classes, file_decls,
                             project_method_decls):
            total_modified += 1
            print(f"  Modified: {rel_path}")

    # Clean target/ directories
    removed = clean_target_dirs(output_dir)
    if removed:
        print(f"Cleaned {len(removed)} target director(ies)")

    print(f"\nDone: {len(java_files)} files processed, {total_modified} modified")
    print(f"Output: {output_dir}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Handle Cangjie keyword conflicts in Java code')
    ap.add_argument('--project', type=str, required=True, help='project name')
    args = ap.parse_args()
    main(args)
