#!/usr/bin/env python3
"""Shared utilities for Java preprocessing scripts."""
import os
import shutil
from tree_sitter import Language, Parser


def load_parser():
    """Load tree-sitter parser for Java."""
    parser = Parser()
    try:
        import tree_sitter_java

        language = Language(tree_sitter_java.language())
    except Exception:
        if not os.path.exists('misc/parser/language.so'):
            lib_dir = 'misc/sitter-libs'
            libs = [os.path.join(lib_dir, d) for d in os.listdir(lib_dir)]
            Language.build_library('misc/parser/language.so', libs)
        language = Language('misc/parser/language.so', 'java')
    if hasattr(parser, 'set_language'):
        parser.set_language(language)
    else:
        parser.language = language
    return parser


def extract_text_by_bytes(code, start_byte, end_byte):
    """Extract text from code bytes."""
    return code[start_byte:end_byte].decode('utf-8')


def _skip_dir(root):
    """Check if a directory should be skipped (target/, benchmarks/)."""
    parts = root.split(os.sep)
    return 'target' in parts or 'benchmarks' in parts


def clean_target_dirs(output_dir):
    """Remove all target/ directories."""
    removed = []
    for root, dirs, files in os.walk(output_dir):
        if os.path.basename(root) == 'target':
            shutil.rmtree(root)
            removed.append(root)
            dirs.clear()
    return removed


def pre_scan_project(output_dir, active_keywords=None, collect_method_decls=False):
    """
    Pre-scan all Java files to collect:
    - user_classes: set of user-defined class names
    - file_decls:   dict of file_path -> set of declared names matching active keywords
    - project_method_decls: set of active keyword names declared as methods anywhere in the
                            project (only populated when collect_method_decls=True)
    """
    parser = load_parser()
    user_classes = set()
    file_decls = {}
    project_method_decls = set()

    for root, dirs, files in os.walk(output_dir):
        if _skip_dir(root):
            continue
        for fname in files:
            if not fname.endswith('.java'):
                continue
            file_path = os.path.join(root, fname)
            with open(file_path, 'rb') as f:
                code = f.read()
            tree = parser.parse(code)

            classes = set()
            decls = set()
            file_methods = set() if collect_method_decls else None
            _scan_node(tree.root_node, code, classes, decls, active_keywords,
                       file_methods)
            user_classes.update(classes)
            file_decls[file_path] = decls
            if file_methods:
                project_method_decls.update(file_methods)

    if collect_method_decls:
        return parser, user_classes, file_decls, project_method_decls
    return parser, user_classes, file_decls


def _scan_node(node, code, user_classes, declarations, active_keywords=None,
               file_methods=None):
    """Recursively collect class names + declaration sites of active keywords.

    When *file_methods* is provided (a set), active keyword names declared as
    methods/constructors are added to it.  This is used by the keyword conflict
    handler to distinguish project-internal method calls from JDK/external ones.
    """
    nt = node.type

    if nt in ('class_declaration', 'interface_declaration',
              'enum_declaration', 'record_declaration'):
        name_node = node.child_by_field_name('name')
        if name_node:
            user_classes.add(extract_text_by_bytes(code,
                                                   name_node.start_byte,
                                                   name_node.end_byte))

    if active_keywords:
        if nt == 'variable_declarator':
            name_node = node.child_by_field_name('name')
            if name_node:
                text = extract_text_by_bytes(code, name_node.start_byte,
                                             name_node.end_byte)
                if text in active_keywords:
                    declarations.add(text)

        if nt in ('method_declaration', 'constructor_declaration'):
            name_node = node.child_by_field_name('name')
            if name_node:
                text = extract_text_by_bytes(code, name_node.start_byte,
                                             name_node.end_byte)
                if text in active_keywords:
                    declarations.add(text)
                    if file_methods is not None:
                        file_methods.add(text)

        if nt == 'formal_parameter':
            name_node = node.child_by_field_name('name')
            if name_node:
                text = extract_text_by_bytes(code, name_node.start_byte,
                                             name_node.end_byte)
                if text in active_keywords:
                    declarations.add(text)

        if nt == 'lambda_parameter':
            for child in node.children:
                if child.type in ('identifier', 'type_identifier'):
                    text = extract_text_by_bytes(code, child.start_byte,
                                                 child.end_byte)
                    if text in active_keywords:
                        declarations.add(text)

    for child in node.children:
        _scan_node(child, code, user_classes, declarations, active_keywords,
                   file_methods)
