import re
import json
import pytest

def read_dot_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

def parse_dot_content(dot_content, target):
    parent_nodes = []
    pattern = re.compile(r"(\w+)\s*->\s*(\w+)")
    for match in pattern.findall(dot_content):
        parent, child = match
        if child == target:
            parent_nodes.append(parent)
    return parent_nodes

def read_cluster_1_content(dot_content):
    cluster_1_pattern = re.compile(r'subgraph cluster_1 {([\s\S]*?)}\n', re.MULTILINE)
    match = cluster_1_pattern.search(dot_content)
    if match:
        return match.group(1)
    else:
        return None

def parse_output_dot_content(cluster_1_content, target):
    output_parent_nodes = []
    output_parent_nodes.append('output')
    pattern = re.compile(r"(\w+)\s*->\s*(\w+)")
    
    for match in pattern.findall(cluster_1_content):  # Using cluster_1_content here
        parent, child = match
        if child:
            output_parent_nodes.append(child)
            print("output",output_parent_nodes)
            
    return output_parent_nodes

dot_file_path = "/home/saheli/work_collection/generated_by_graph_on_draw_6feaeffee44d4390b3f18293a4436825/image"  
dot_content = read_dot_file(dot_file_path)
cluster_1_content = read_cluster_1_content(dot_content)
print("cluster_1_content",cluster_1_content)

json_file_path = "parent_entries_dict.json" 
json_file_path_output = "output_parent_entries_dict.json" 

with open(json_file_path, 'r') as f:
    json_data = json.load(f)

with open(json_file_path_output, 'r') as f:
    json_data_output_entries = json.load(f)

target = "image_classification_using_tf_py"
dot_relationships = {target: parse_dot_content(dot_content, target)}
dot_output_relationships = {target: parse_output_dot_content(cluster_1_content, target)}

def test_compare_dot_and_json_for_target():
    assert set(json_data.get(target, [])) == set(dot_relationships.get(target, []))

def check_output_child_exists(dot_content):
    pattern = re.compile(r"output\s+\[color=blue style=filled\]")
    match = pattern.search(dot_content)
    return bool(match)

def test_compare_dot_and_json_for_target_output():
    assert set(json_data_output_entries.get(target, [])).issubset(set(dot_output_relationships.get(target, [])))

    # Assertion to ensure 'output' exists in cluster_1 if output_parent_entries are present.
    if json_data_output_entries.get(target, []):
        assert check_output_child_exists(dot_content)
    
pytest.main(["-v", "-s"])
