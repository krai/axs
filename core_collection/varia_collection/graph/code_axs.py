import subprocess
import sys
import os
import logging
import re
import graphviz
from kernel import default_kernel as ak

def draw_collection(collection_object, tone_colour, graph):
    collection_name = collection_object.get_name()

    cluster = graphviz.Digraph(name='cluster_'+collection_name)
    cluster.attr(style='filled', color=tone_colour, fillcolor=tone_colour)

    collection_entry_names = collection_object['contained_entries'].keys()

    for entry_name in collection_entry_names:
        entry = ak.byname(entry_name)
        own_data = entry.own_data()
        tags = own_data.get('tags', '')
        label = f"{entry_name} {tags}"

        if '_producer_rules' in own_data:
            cluster.node(entry_name, label=label, shape='rectangle')
        else:
            cluster.node(entry_name, label=label)

        for p in entry.get('_parent_entries', []):
            if p:
                graph.edge(entry_name+':w', p.get_name()+':e')
            else:
                print(collection_name, entry_name)
                graph.node('BROKEN_PARENT', style='filled', color='red')
                graph.edge(entry_name+':w', 'BROKEN_PARENT:e')

    graph.subgraph(cluster)


def dfs(root, f, __entry__):
    stack = []
    visited = set()

    cur_target_entry = __entry__.get_kernel().byname(root)
    if not cur_target_entry:
        print("ERROR!")
        return 
    stack.append((cur_target_entry, 0))
    
    while stack:
        cur_target_entry, level = stack.pop()
        cur_target = cur_target_entry.get_name()
        print(cur_target)
        if cur_target in visited:
            continue

        f.node(cur_target)
        visited.add(cur_target)

        parents = cur_target_entry.get("_parent_entries")
        if parents:
            for parent in parents:
                if isinstance(parent, str):
                    p = __entry__.get_kernel().byname(parent)
                else:
                    p = parent
                if not p:
                    continue
                stack.append((p, 0))
                f.node(p.get_name())
                f.edge(p.get_name(), cur_target)

    return f

def draw(target, return_this_entry=None, __entry__=None):
    dest_dir = return_this_entry.get_path()
    target_entry = __entry__.get_kernel().byname(target)
    output = False
    output_parents_data = ""
    target_data = target_entry.own_data()

    for key, val in target_data.items():
        if "_parent_entries" in str(val):
            output = True
            output_parents_data = val
        elif "tags" in str(val):
            output = True

    f = graphviz.Digraph(format='png')
    f.attr('node', shape='circle')
    f = dfs(target, f, __entry__)
    if output:
        f.node("output")
        f.edge(target, "output")

    if output_parents_data:
        info = find_parent(output_parents_data)
        output_parents = find_byname(info)
        print("output_parents", output_parents)
        for output_parent in output_parents:
            f = dfs(output_parent, f, __entry__)
            f.edge(output_parent, "output")
            target_entry = output_parent
        else:
            target_entry = None

        

    f.render(filename=f"{dest_dir}/image")
    return return_this_entry

def find_parent(obj):
    # obj = ['^^', 'execute', [[['get', '__record_entry__'], ['attach', ['^', 'work_collection']], ['plant', ['^^', 'substitute', [["_parent_entries", ['AS^IS', 'AS^IS', ['^', 'byname', 'base_bert_experiment']], 'tags', ['program_output', 'bert_squad'], 'model_name', '#{model_name}#', 'framework', '#{framework}#', 'output_file_name', '#{output_file_name}#', 'desired_python_version', '#{desired_python_version}#']]]], ['save'], ['get_path_from', 'output_file_name']]]] 
    items = find_key(obj, "_parent_entries")
    return items

def find_byname(obj=None):
    obj = ['_parent_entries', ['AS^IS', 'AS^IS', ['^', 'byname', 'base_bert_loadgen_experiment'], ["^", "byname", "base_qaic_experiment"]], 'tags', ['program_output', 'bert_squad'], 'model_name', '#{model_name}#', 'framework', '#{framework}#', 'output_file_name', '#{output_file_name}#', 'desired_python_version', '#{desired_python_version}#']
    items = find_key(obj, "byname")
    return [list(item)[2] for item in items]

def find_key(obj, key):
    matches = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            matches.extend(find_key(v, key))
            result = find_key(v, key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        if key == "_parent_entries" and re.search(r"^\[(?:'|\")_parent_entries(.*)", str(obj)):
            matches.append(obj)
        if key == "byname" and re.search(r"^\[(?:'|\")\^(?:'|\")(?:\s*),(?:\s*)(?:'|\")byname(.*)", str(obj)):
            matches.append(obj)
        for item in obj:
            matches.extend(find_key(item, key))

    return matches
        


