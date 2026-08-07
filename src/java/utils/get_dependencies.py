import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.java.utils.get_schema_file import get_schema_file

def build_inheritance_map(args):
    inheritance = {}  # maps class_name -> list of superclasses/interfaces

    for schema_file in os.listdir(args.schemas_dir):
        full_path = os.path.join(args.schemas_dir, schema_file)
        if not schema_file.endswith('.json'):
            continue
        with open(full_path, 'r') as f:
            schema = json.load(f)

        class_dict = schema.get("classes", {})
        for key, class_info in class_dict.items():
            class_name = key.split(":")[-1]
            superclasses = class_info.get("extends", [])
            interfaces = class_info.get("implements", [])
            inheritance[class_name] = superclasses + interfaces

    return inheritance


def get_dependencies(args):

    call_graph = []
    with open(f'data/java/call_graphs/{args.project}/callgraph.txt', 'r') as f:
        call_graph = f.readlines()
    call_graph = [line.strip()[2:] for line in call_graph if line.strip().startswith('C:')]

    dependencies = {}
    for schema_file in os.listdir(args.schemas_dir):
        partial_path = schema_file.replace(f'{args.project}.', '', 1).replace('.json', '')
        partial_path = partial_path.replace('src.main.', '').replace('src.test.', '')
        dependencies.setdefault(partial_path, [])

    inheritance_map = build_inheritance_map(args)

    class_to_path = {}  # class_name -> partial_path

    for schema_file in os.listdir(args.schemas_dir):
        partial_path = schema_file.replace(f'{args.project}.', '', 1).replace('.json', '')
        partial_path = partial_path.replace('src.main.', '').replace('src.test.', '')

        with open(os.path.join(args.schemas_dir, schema_file), 'r') as f:
            schema = json.load(f)

        for key in schema.get("classes", {}):
            class_name = key.split(":")[-1]
            class_to_path[class_name] = partial_path

    for schema_file in os.listdir(args.schemas_dir):
        partial_path = schema_file.replace(f'{args.project}.', '', 1).replace('.json', '')
        partial_path = partial_path.replace('src.main.', '').replace('src.test.', '')
        class_name = partial_path.split('.')[-1]
        inherited = inheritance_map.get(class_name, [])

        for parent in inherited:
            parent_path = class_to_path.get(parent)
            if parent_path and [parent, parent_path] not in dependencies[partial_path]:
                dependencies[partial_path].append([parent, parent_path])


    for l in call_graph:
        caller, callee = l.split()

        if '$' in caller:
            caller = caller.split('$')[0]

        for i in range(1, 10):
            if f'${i}' in callee:
                callee = callee.replace(f'${i}', '')
                break

        dependencies.setdefault(caller, [])
        
        if caller == callee:
            continue

        callee_partial_path = callee
        callee_class_name = callee.split('.')[-1]

        if '$' in callee:
            callee_partial_path = callee.split('$')[0]
            callee_class_name = callee.split('$')[1]
                
        if caller == callee_partial_path:
            continue
        
        schema_file = get_schema_file(args.project, callee_partial_path, args)

        if not schema_file:
            continue

        if [callee_class_name, callee_partial_path] not in dependencies[caller]:
            dependencies[caller].append([callee_class_name, callee_partial_path])
        
    
    return dependencies
