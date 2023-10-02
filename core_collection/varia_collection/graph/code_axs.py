import subprocess
import sys
import os
import logging
import re
import graphviz
import json
from kernel import default_kernel as ak

initial_root_visited = False

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


def dfs(root, f, __entry__, is_output=False):
    global initial_root_visited
    stack = []
    visited = set()

    cur_target_entry = __entry__.get_kernel().byname(root)
    if not cur_target_entry:
        print("ERROR!")
        return 

    stack.append((cur_target_entry, True))  # Using True to signify that this is the initial root node
    
    while stack:
        cur_target_entry, is_initial_root = stack.pop()
        cur_target = cur_target_entry.get_name()

        if cur_target in visited:
            continue

        if not initial_root_visited:
            color = 'red'
            initial_root_visited = True
        elif is_output:
            color = 'lightblue'
        else:
            color = 'lightcoral'

        f.node(cur_target, color=color, style='filled')
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
                stack.append((p, False))  # Using False to signify that this is not the initial root node
                f.edge(p.get_name(), cur_target)
    
    return f

def draw(target, return_this_entry=None, __entry__=None):

    global initial_root_visited
    initial_root_visited = False
    dest_dir = return_this_entry.get_path()
    target_entry = __entry__.get_kernel().byname(target)
    print("target_entry",target_entry)
    get_path = target_entry.get_path()
    file_path = f'{get_path}/data_axs.json'
    
    output = False
    output_parents_data = ""
    target_data = target_entry.own_data()

    output_entries = target_entry.get("output_entry_parents")
    print("output_entries:", output_entries)

    # Extract all 'byname' entries from "output_entry_parents" as a key
    if output_entries:
        byname_entries = extract_byname_entries(output_entries)
        print("byname_entries:", byname_entries)


    for key, val in target_data.items():
        if "_parent_entries" in str(val):
            output = True
            output_parents_data = val
        elif "tags" in str(val):
            output = True
        elif output_entries:
            output = True

    f = graphviz.Digraph(format='png')
    f.attr('node', shape='circle')

    with f.subgraph(name='cluster_0') as c:
        c.attr(style='dotted')
        c.attr(label='Group A')
        dfs(target, c, __entry__, is_output=False)  
 

    if output:
        f.node("output", style='filled', color='blue')
        f.edge(target, "output")

    if output_parents_data:
        info = find_parent(output_parents_data)
        output_parents = find_byname(file_path,obj=info)
        print("output_parents", output_parents)
        for output_parent in output_parents:
            with f.subgraph(name='cluster_1') as c:
                c.attr(style='dotted')
                c.attr(label='Group B')
                dfs(output_parent, c, __entry__, is_output=True) 
                f.edge(output_parent, "output")
                target_entry = output_parent
        else:
            target_entry = None

    elif output_entries and byname_entries:
        for byname_entry in byname_entries:
            with f.subgraph(name=f'cluster_1') as c:
                c.attr(style='dotted')
                c.attr(label=f'Group B')
                dfs(byname_entry, c, __entry__, is_output=True)  
                f.edge(byname_entry, "output")


    f.render(filename=f"{dest_dir}/image")
    return return_this_entry

def find_parent(obj):
    items = find_key(obj, "_parent_entries")
    return items

def find_byname(file_path, obj=None):
    obj=process_json(file_path)
    items = find_key(obj, "byname")
    print("items",items)
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
            
def process_json(file_path):
    with open(file_path) as f:
        obj = json.load(f)
        required_data = {key: obj[key] for key in ['output_file_path', 'output_entry'] if key in obj}
        parents = find_parent(required_data)
    return parents


def extract_byname_entries(output_entries):
    byname_entries = []
    for item in output_entries:
        if isinstance(item, list) and 'byname' in item:
            index = item.index('byname') + 1
            if index < len(item):
                byname_entries.append(item[index])
    return byname_entries

