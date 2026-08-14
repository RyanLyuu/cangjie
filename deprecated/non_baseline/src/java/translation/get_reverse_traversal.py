import os
import json


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _should_include_test_fragments(args):
    return _as_bool(getattr(args, "translate_tests", False))


def _is_test_schema(schema_name):
    return (
        ".src.test." in schema_name
        or schema_name.endswith(".src.test")
        or ".evosuite-tests." in schema_name
    )


def _field_name_from_key(field_key):
    return field_key.split(":", 1)[1].strip() if ":" in field_key else field_key.strip()


def _is_framework_ignored_field(field_key):
    return _field_name_from_key(field_key).startswith("serialVersionUID")


def order_fragments(project_traversal):
    """
    Order the fragments - keep traversal.json order, move test methods to end.
    """
    test_methods_order = []
    for fragment in project_traversal.copy():
        if fragment["fragment_type"] == "method" and fragment.get("is_test_method"):
            test_methods_order.append(fragment)
            project_traversal.remove(fragment)
    return project_traversal + test_methods_order


def process_waiting_queue(
    waiting_queue, processed_fragments, project_traversal, max_threshold=10
):
    """
    Process the waiting queue to check if any fragment can be processed
    """
    threshold = max_threshold
    while True:
        if len(waiting_queue) == 0:
            break

        if threshold == 0:
            break

        for waiting_fragment in list(waiting_queue.keys()):
            waiting_dependent_fragments = [
                x for x in waiting_queue[waiting_fragment][0]
            ]
            if all([x in processed_fragments for x in waiting_dependent_fragments]):
                (
                    _,
                    waiting_schema,
                    waiting_class,
                    waiting_method,
                    is_test_method,
                    is_constructor,
                    signature,
                ) = _unpack_waiting_fragment(waiting_queue[waiting_fragment])

                processed_fragments.append(waiting_fragment)
                del waiting_queue[waiting_fragment]
                project_traversal.append(
                    {
                        "schema_name": waiting_schema,
                        "class_name": waiting_class,
                        "fragment_name": waiting_method,
                        "fragment_type": "method",
                        "is_test_method": is_test_method,
                        "is_constructor": is_constructor,
                        "signature": signature,
                    }
                )
                threshold = max_threshold

        threshold -= 1

    return waiting_queue, processed_fragments, project_traversal


def _unpack_waiting_fragment(item):
    if len(item) == 7:
        return item
    if len(item) == 6:
        dependent_fragments, schema, class_, method, is_test_method, signature = item
        return (
            dependent_fragments,
            schema,
            class_,
            method,
            is_test_method,
            False,
            signature,
        )
    raise ValueError(f"Unexpected waiting queue entry length: {len(item)}")


def get_field_order(data, class_):
    """
    Get the order of fields based on dependencies
    """
    field_dependencies = {}
    for field in data["classes"][class_]["fields"]:
        field_dependencies.setdefault(field, [])
        for field_ in data["classes"][class_]["fields"]:
            if field == field_:
                continue
            if "=" not in "".join(data["classes"][class_]["fields"][field]["body"]):
                continue
            if (
                field_
                in "".join(
                    "".join(data["classes"][class_]["fields"][field]["body"]).split(
                        "="
                    )[1:]
                ).strip()
            ):
                field_dependencies[field].append(field_)

    field_order = []
    while len(field_order) != len(data["classes"][class_]["fields"]):
        for field in data["classes"][class_]["fields"]:
            if field in field_order:
                continue
            if all([x in field_order for x in field_dependencies[field]]):
                field_order.append(field)

    return field_order


def unroll_cycles(waiting_queue, processed_fragments, project_traversal):
    """
    Unroll cycles in the waiting queue, if any
    """
    cycles = []
    # detect cycles in the waiting queue
    for k in waiting_queue:
        (
            waiting_dependent_fragments,
            waiting_schema,
            waiting_class,
            waiting_method,
            is_test_method,
            is_constructor,
            signature,
        ) = _unpack_waiting_fragment(waiting_queue[k])

        for df in waiting_dependent_fragments:
            if df not in waiting_queue:
                continue

            if (
                k in waiting_queue[df][0]
                and df in waiting_queue[k][0]
                and [df, k] not in cycles
            ):
                cycles.append([k, df])

    # translating elements of cycles one by one
    for cycle in cycles:
        for cycle_fragment in cycle:
            (
                waiting_dependent_fragments,
                waiting_schema,
                waiting_class,
                waiting_method,
                is_test_method,
                is_constructor,
                signature,
            ) = _unpack_waiting_fragment(waiting_queue[cycle_fragment])

            processed_fragments.append(cycle_fragment)
            del waiting_queue[cycle_fragment]

            project_traversal.append(
                {
                    "schema_name": waiting_schema,
                    "class_name": waiting_class,
                    "fragment_name": waiting_method,
                    "fragment_type": "method",
                    "is_test_method": is_test_method,
                    "is_constructor": is_constructor,
                    "signature": signature,
                }
            )


def get_reverse_traversal(args):
    """
    Get the traversal of the project based on class order defined in traversal.json

    The traversal.json file defines the order in which classes should be translated:
    - Fields and static initializers are processed first for each class
    - Methods are processed in class order, but with dependency checking
    - Classes are processed in the order defined in traversal.json
    """
    project_traversal = []
    schemas = os.listdir(args.translation_dir)
    include_tests = _should_include_test_fragments(args)

    # Load class order from traversal.json if available
    traversal_order_path = f"data/java/dependencies{args.suffix}/{args.project}/traversal.json"
    class_order = []
    try:
        with open(traversal_order_path, "r") as f:
            class_order = json.load(f)
        class_order = [
            class_order[key]
            for key in sorted(class_order, key=lambda k: int(k))
        ]
    except FileNotFoundError:
        class_order = []

    # Build a map of class_name -> class_order_index for fast lookup
    class_order_index_map = {}
    for idx, class_name in enumerate(class_order):
        class_order_index_map[class_name] = idx

    # Load all schema data first
    all_schema_data = {}
    for schema in schemas:
        if not schema.endswith(".json"):
            continue

        schema_base_name = schema[:-5]

        if _is_test_schema(schema_base_name) and not include_tests:
            continue

        if args.translate_evosuite and "ESTest" not in schema:
            continue

        if not args.translate_evosuite and "ESTest" in schema:
            continue

        path_ = f"{args.translation_dir}/{schema}"
        with open(path_, "r") as f:
            data = json.load(f)
            all_schema_data[schema_base_name] = data

    if not class_order:
        # Original dependency-based traversal
        waiting_queue = {}
        processed_fragments = []

        for schema in schemas:
            if not schema.endswith(".json"):
                continue

            schema_base_name = schema[:-5]

            if _is_test_schema(schema_base_name) and not include_tests:
                continue

            if args.translate_evosuite and "ESTest" not in schema:
                continue

            if not args.translate_evosuite and "ESTest" in schema:
                continue

            path_ = f"{args.translation_dir}/{schema}"
            with open(path_, "r") as f:
                data = json.load(f)

            for class_ in data["classes"]:
                if "new" in class_ or "{" in class_:
                    continue

                field_order = get_field_order(data, class_)

                for field_ in field_order:
                    if _is_framework_ignored_field(field_):
                        continue
                    project_traversal.append(
                        {
                            "schema_name": schema_base_name,
                            "class_name": class_,
                            "fragment_name": field_,
                            "fragment_type": "field",
                            "is_test_method": False,
                        }
                    )

                if "static_initializers" in data["classes"][class_]:
                    for static_initializer in data["classes"][class_][
                        "static_initializers"
                    ]:
                        project_traversal.append(
                            {
                                "schema_name": schema_base_name,
                                "class_name": class_,
                                "fragment_name": static_initializer,
                                "fragment_type": "static_initializer",
                                "is_test_method": False,
                            }
                        )

                for method_ in data["classes"][class_]["methods"]:
                    full_fragment_name = f"{schema_base_name}|{class_}|{method_}"
                    dependent_fragments = [
                        f"{x[0]}|{x[1]}|{x[2]}"
                        for x in data["classes"][class_]["methods"][method_]["calls"]
                        if ":" in x[2] and full_fragment_name != f"{x[0]}|{x[1]}|{x[2]}"
                    ]

                    # Check if class name ends with _test (test class)
                    actual_class_name = class_.split(":")[-1]
                    is_test_method = actual_class_name.endswith("_test")
                    if is_test_method and not include_tests:
                        continue

                    if (
                        any([x not in processed_fragments for x in dependent_fragments])
                        and not args.translate_evosuite
                    ):
                        waiting_queue[full_fragment_name] = [
                            dependent_fragments,
                            schema_base_name,
                            class_,
                            method_,
                            is_test_method,
                            data["classes"][class_]["methods"][method_].get("is_constructor", False),
                            data["classes"][class_]["methods"][method_].get("signature", ""),
                        ]
                        continue

                    processed_fragments.append(full_fragment_name)
                    project_traversal.append(
                        {
                            "schema_name": schema_base_name,
                            "class_name": class_,
                            "fragment_name": method_,
                            "fragment_type": "method",
                            "is_test_method": is_test_method,
                            "is_constructor": data["classes"][class_]["methods"][method_].get("is_constructor", False),
                            "signature": data["classes"][class_]["methods"][method_].get("signature", ""),
                        }
                    )

                    waiting_queue, processed_fragments, project_traversal = (
                        process_waiting_queue(
                            waiting_queue, processed_fragments, project_traversal, 1
                        )
                    )

        waiting_queue, processed_fragments, project_traversal = process_waiting_queue(
            waiting_queue, processed_fragments, project_traversal
        )

        if len(waiting_queue) == 0:
            return order_fragments(project_traversal)

        unroll_cycles(waiting_queue, processed_fragments, project_traversal)
        waiting_queue, processed_fragments, project_traversal = process_waiting_queue(
            waiting_queue, processed_fragments, project_traversal
        )

        return order_fragments(project_traversal)

    # With traversal.json: process by class order
    processed_fragments = []
    waiting_queue = {}

    classes_by_order = {}
    unordered_classes = []
    for schema_base_name, data in all_schema_data.items():
        for class_ in data["classes"]:
            if "new" in class_ or "{" in class_:
                continue
            actual_class_name = class_.split(":")[-1] if ":" in class_ else class_
            if actual_class_name in class_order_index_map:
                order_idx = class_order_index_map[actual_class_name]
                if order_idx not in classes_by_order:
                    classes_by_order[order_idx] = []
                classes_by_order[order_idx].append((schema_base_name, class_, data))
            else:
                unordered_classes.append((schema_base_name, class_, data))

    class_batches = [classes_by_order[order_idx] for order_idx in sorted(classes_by_order.keys())]
    if unordered_classes:
        class_batches.append(unordered_classes)

    for class_batch in class_batches:
        for schema_base_name, class_, data in class_batch:
            field_order = get_field_order(data, class_)
            for field_ in field_order:
                if _is_framework_ignored_field(field_):
                    continue
                processed_fragments.append(f"{schema_base_name}|{class_}|{field_}")
                project_traversal.append(
                    {
                        "schema_name": schema_base_name,
                        "class_name": class_,
                        "fragment_name": field_,
                        "fragment_type": "field",
                        "is_test_method": False,
                    }
                )

            if "static_initializers" in data["classes"][class_]:
                for static_initializer in data["classes"][class_][
                    "static_initializers"
                ]:
                    processed_fragments.append(f"{schema_base_name}|{class_}|{static_initializer}")
                    project_traversal.append(
                        {
                            "schema_name": schema_base_name,
                            "class_name": class_,
                            "fragment_name": static_initializer,
                            "fragment_type": "static_initializer",
                            "is_test_method": False,
                        }
                    )

            for method_ in data["classes"][class_]["methods"]:
                full_fragment_name = f"{schema_base_name}|{class_}|{method_}"

                dependent_fragments = [
                    f"{x[0]}|{x[1]}|{x[2]}"
                    for x in data["classes"][class_]["methods"][method_]["calls"]
                    if ":" in x[2] and full_fragment_name != f"{x[0]}|{x[1]}|{x[2]}"
                ]

                # Check if class name ends with _test (test class)
                actual_class_name = class_.split(":")[-1]
                is_test_method = actual_class_name.endswith("_test")
                if is_test_method and not include_tests:
                    continue

                if any([x not in processed_fragments for x in dependent_fragments]):
                    waiting_queue[full_fragment_name] = [
                        dependent_fragments,
                        schema_base_name,
                        class_,
                        method_,
                        is_test_method,
                        data["classes"][class_]["methods"][method_].get("is_constructor", False),
                        data["classes"][class_]["methods"][method_].get("signature", ""),
                    ]
                    continue

                processed_fragments.append(full_fragment_name)
                project_traversal.append(
                    {
                        "schema_name": schema_base_name,
                        "class_name": class_,
                        "fragment_name": method_,
                        "fragment_type": "method",
                        "is_test_method": is_test_method,
                        "is_constructor": data["classes"][class_]["methods"][method_].get("is_constructor", False),
                        "signature": data["classes"][class_]["methods"][method_].get("signature", ""),
                    }
                )

    waiting_queue, processed_fragments, project_traversal = process_waiting_queue(
        waiting_queue, processed_fragments, project_traversal
    )

    if len(waiting_queue) > 0:
        unroll_cycles(waiting_queue, processed_fragments, project_traversal)
        waiting_queue, processed_fragments, project_traversal = process_waiting_queue(
            waiting_queue, processed_fragments, project_traversal
        )

    return order_fragments(project_traversal)
