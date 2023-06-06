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

    f = graphviz.Digraph(format='png')
    f.attr('node', shape='circle')
    f = dfs(target, f, __entry__)

    f.render(filename=f"{dest_dir}/image")
    return return_this_entry


def find_parent(obj):
    # obj = ['^^', 'execute', [[['get', '__record_entry__'], ['attach', ['^', 'work_collection']], ['plant', ['^^', 'substitute', [["_parent_entries", ['AS^IS', 'AS^IS', ['^', 'byname', 'base_bert_experiment']], 'tags', ['program_output', 'bert_squad'], 'model_name', '#{model_name}#', 'framework', '#{framework}#', 'output_file_name', '#{output_file_name}#', 'desired_python_version', '#{desired_python_version}#']]]], ['save'], ['get_path_from', 'output_file_name']]]] 
    item = find_key(obj, "_parent_entries")
    return item

def find_byname(obj=None):
    obj = ['_parent_entries', ['AS^IS', 'AS^IS', ['^', 'byname', 'base_bert_experiment']], 'tags', ['program_output', 'bert_squad'], 'model_name', '#{model_name}#', 'framework', '#{framework}#', 'output_file_name', '#{output_file_name}#', 'desired_python_version', '#{desired_python_version}#']
    item = find_key(obj, "byname")

    return list(item)[2]

def find_key(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            result = find_key(v, key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        if key == "_parent_entries" and re.search(r"^\[(?:'|\")_parent_entries(.*)", str(obj)):
            return obj
        
        if key == "byname" and re.search(r"^\[(?:'|\")\^(?:'|\")(?:\s*),(?:\s*)(?:'|\")byname(.*)", str(obj)):
            return obj
        
        
        for item in obj:
            result = find_key(item, key)
            if result is not None:
                return result
    return None



