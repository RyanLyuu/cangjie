
def topological_sort(graph: list[tuple[str, str]]) -> list[str]:
    """
    Provides a topological sort of the graph.

    Args:
        graph: A list of tuples where each tuple contains two strings representing the source and target nodes.

    Returns:
        A list of strings representing the nodes in topological order.
    """
    # create a dictionary with the nodes as keys and their dependencies as values
    graph_dict = {}
    for edge in graph:
        if edge[0] not in graph_dict:
            graph_dict[edge[0]] = []
        graph_dict[edge[0]].append(edge[1])

    # create a dictionary with the nodes as keys and their indegree as values
    indegree_dict = {}
    for edge in graph:
        if edge[1] not in indegree_dict:
            indegree_dict[edge[1]] = 0
        if edge[0] not in indegree_dict:
            indegree_dict[edge[0]] = 0
        indegree_dict[edge[1]] += 1

    # create a list of nodes with indegree 0
    zero_indegree = [node for node in indegree_dict if indegree_dict[node] == 0]

    # create a list to store the sorted nodes
    sorted_nodes = []

    # loop over the nodes with indegree 0
    while zero_indegree:
        node = zero_indegree.pop()
        sorted_nodes.append(node)

        # loop over the nodes that depend on the current node
        if node in graph_dict:
            for dependent_node in graph_dict[node]:
                indegree_dict[dependent_node] -= 1
                if indegree_dict[dependent_node] == 0:
                    zero_indegree.append(dependent_node)

    return sorted_nodes


def get_class_order(schema_data):
    """
    Get the order of classes in the schema based on inheritance.
    """
    dependency_graph = []
    
    for class_ in schema_data['classes']:
        for parent in schema_data['classes'][class_]['extends']:
            parent_key = ''
            for key in schema_data['classes']:
                if key.split(':')[1] == parent:
                    parent_key = key
                    break
            if parent_key in schema_data['classes']:
                dependency_graph.append((class_, parent_key))
            
        for interface in schema_data['classes'][class_]['implements']:
            interface_key = ''
            for key in schema_data['classes']:
                if key.split(':')[1] == interface:
                    interface_key = key
                    break
            if interface_key in schema_data['classes']:
                dependency_graph.append((class_, interface_key))
        
        if schema_data['classes'][class_]['nested_inside']:
            dependency_graph.append((class_, schema_data['classes'][class_]['nested_inside']))
        
    class_list = topological_sort(dependency_graph)[::-1]
    # check for any classes that were not included in the dependency graph
    class_list += [clz for clz in schema_data['classes'] if clz not in class_list]

    return class_list
