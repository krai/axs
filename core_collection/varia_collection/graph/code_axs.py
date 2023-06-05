import subprocess
import sys
import os
import logging
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

import re

def draw(target, return_this_entry=None, __entry__=None):
    # To view graph
    # display $(axs byquery graph_output,target=bert_squad_onnxruntime_py , get_path)/image.png

    # __record_entry__.attach(__entry__.get_kernel().byname("work_collection"))
    # __record_entry__.plant('tags', ['graph_output'])
    # __record_entry__.save()
    dest_dir = return_this_entry.get_path()
    cur_target = target
    
    while(cur_target):
    
        cur_target_entry = __entry__.get_kernel().byname(cur_target)
        print(f"cur_target: {cur_target_entry}")
        parents = cur_target_entry.get("_parent_entries")
        # print(f"Parent(s): {parents}")
        output_entry = cur_target_entry.get("output_file_name")
        # print(f"Output: {output_entry}")

        f = graphviz.Digraph(format='png')
        f.attr('node', shape='circle')
        f.node(cur_target)

        output = False
        output_parents_data = ""
        cur_target_data = cur_target_entry.own_data()
        for key, val in cur_target_data.items():
            if "_parent_entries" in str(val):
                output = True
                output_parents_data = val
            elif "tags" in str(val):
                output = True

        stack = []

        # Add parent objects to the stack
        if parents:
            for parent in parents:
                stack.append((parent, 0))  # (object, level)

        visited = set()  # Track visited parent objects
        parent_entries = {0: []}  # Parent entries dictionary for each level
        parents_check = []
        while stack != []:
            parent, level = stack.pop()
            print(f"stack: {parent.get_name()}, level: {level}")
            print(type(parent))
            parent_entry_check = __entry__.get_kernel().byname(parent)
            print(f"parent_entry_check: {parent_entry_check}")
            if parent_entry_check:
                parents_check = parent_entry_check.get("_parent_entries")
                print(f"parent_entries: {parents_check}")

            if parents_check:

                # Add parent objects to the graph
                if parent and __entry__.get_kernel() and __entry__.get_kernel().byname(parent):
                    parent_entries[level] = parent.get_kernel().byname(parent).get("_parent_entries")
                    for grandparent in parent_entries[level]:
                        f.node(grandparent.get_name())
                        f.edge(grandparent.get_name(), parent.get_name())
                        if grandparent not in visited:  # Check if grandparent has been visited
                            stack.append((grandparent, level + 1))
            else:
                print(f"No parent entries for {parent.get_name()}")
                f.node(parent.get_name())
                f.edge(parent.get_name(), cur_target)
            
            
            visited.add(parent)  # Mark parent as visited
            print(f"Visited Array: {visited}")

        print("Stack after iteration:", stack)
        print("Visited set:", visited)

    

        if output:
            f.node("output")
            f.edge(cur_target, "output")

        if output_parents_data:
            info = find_parent(output_parents_data)
            output_parents = find_byname(info)
            f.node(output_parents)
            f.edge(output_parents, "output")
            cur_target_entry = output_parents
        else:
            cur_target_entry = None
    
        break

    f.render(filename=f"{dest_dir}/image", view=True)
    
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



