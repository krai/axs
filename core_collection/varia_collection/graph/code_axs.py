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

def draw(target, __entry__=None, __record_entry__=None, dest_dir="/home/saheli/output"):
    __record_entry__.attach(__entry__.get_kernel().byname("work_collection"))
    __record_entry__.save(dest_dir)

    while(target):
    
        target_entry = __entry__.get_kernel().byname(target)
        print(f"Target: {target_entry}")
        parents = target_entry.get("_parent_entries")
        print(f"Parent(s): {parents}")
        output_entry = target_entry.get("output_file_name")
        print(f"Output: {output_entry}")

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
        f.node(target)

        if parents:
            parent = parents[0]

        while parent:
            f.node(parent.get_name())
            f.edge(parent.get_name(), target_entry.get_name())
            target_entry = parent
            if(target_entry.parents_loaded() and target_entry.parents_loaded()[0]):
                parent = target_entry.parents_loaded()[0]
            else:
                break

        if output:
            f.node("output")
            f.edge(target, "output")

        if output_parents_data:
            info = find_parent(output_parents_data)
            output_parents = find_byname(info)
            f.node(output_parents)
            f.edge(output_parents, "output")
            target = output_parents
        else:
            target = None
    

    f.render(filename=f"{dest_dir}/{target}_entry_hierarchy", view=True)
    __record_entry__.plant("tags", ["graph_output", target])
    
    return __record_entry__

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



