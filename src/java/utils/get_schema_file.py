import os


def get_schema_file(project_name, partial_path, args):
    if os.path.exists(f'{args.schemas_dir}/{project_name}.src.main.{partial_path}.json'):
        return f'{args.schemas_dir}/{project_name}.src.main.{partial_path}.json'
    elif os.path.exists(f'{args.schemas_dir}/{project_name}.src.test.{partial_path}.json'):
        return f'{args.schemas_dir}/{project_name}.src.test.{partial_path}.json'
    else:
        return False
