import re
import graphviz
import json
import networkx as nx
import subprocess
from kernel import default_kernel as ak
from networkx.drawing.nx_pydot import read_dot



initial_root_visited = False 
    
def draw(target, return_this_entry=None, __entry__=None):

    """ Generate Dependency Graph for a given entry.

        Usage examples:
            axs byname graph , draw bert_using_onnxrt_py
            axs byquery graph_output,target=image_classification_using_tf_py
    """

    global initial_root_visited
    initial_root_visited = False
    output = False
    output_parents_data = ""
    dest_dir = return_this_entry.get_path()
   
    target_entry = __entry__.get_kernel().byname(target)

    if target_entry:
        get_path = target_entry.get_path()
        file_path = f'{get_path}/data_axs.json'
        target_data = target_entry.own_data()
        output_entries = target_entry.get("output_entry_parents")

        if output_entries:
            # Extract all 'byname' entries from "output_entry_parents" as objects to byname as key
            byname_entries = extract_byname_entries(output_entries)
            #print("byname_entries:", byname_entries)

        for key, val in target_data.items():
            if "_parent_entries" in str(val):
                output = True
                output_parents_data = val
            elif "tags" in str(val):
                output = True
            elif output_entries:
                output = True

        f = graphviz.Digraph(format='png')
        f.attr('node', shape='ellipse')
        f.attr(dpi='400')
        f.engine = 'dot'

        with f.subgraph(name='cluster_0') as c:
            c.attr(style='dotted')
            c.attr(label='Entry and Its Parent(s)')
            dfs(target, c, __entry__, is_output=False)  
            
        if output:
            f.node("output", style='filled', color='blue')
            f.edge(target, "output")

        if output_parents_data:
            info = find_parent(output_parents_data)
            output_parents = find_byname(file_path,obj=info)
            #print("output_parents", output_parents)
            for output_parent in output_parents:
                with f.subgraph(name='cluster_1') as c:
                    c.attr(style='dotted')
                    c.attr(label='Parent(s) of the Output Entry')
                    dfs(output_parent, c, __entry__, is_output=True) 
                    f.edge(output_parent, "output")
                    target_entry = output_parent
            else:
                target_entry = None

        elif output_entries and byname_entries:
            for byname_entry in byname_entries:
                with f.subgraph(name=f'cluster_1') as c:
                    c.attr(style='dotted')
                    c.attr(label=f'Parent(s) of the Output Entry')
                    dfs(byname_entry, c, __entry__, is_output=True)  
                    f.edge(byname_entry, "output")

        f.render(filename=f"{dest_dir}/image", view=False, cleanup=False)
        print("Graph is generated!")

        return return_this_entry
    else:
        print("ERROR! Provide correct entry name!")

def dfs(root, f, __entry__, is_output=False):

    """ Depth First Search(DFS) for a given node.
    """

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
        cur_target_path = cur_target_entry.get_path()

        if cur_target in visited:
            continue

        if not initial_root_visited:
            color = 'red'
            initial_root_visited = True
        elif is_output:
            color = 'lightblue'
        else:
            color = 'lightcoral'

        f.node(cur_target, label=f'{cur_target}\n{cur_target_path}', color=color, style='filled')
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
                parent_path = p.get_path()
                f.node(p.get_name(), label=f'{p.get_name()}\n{parent_path}', style='filled')
        
    return f

def find_parent(obj):
    items = find_key(obj, "_parent_entries")
    return items

def find_byname(file_path, obj=None):
    obj=process_json(file_path)
    items = find_key(obj, "byname")
    #print("items",items)
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

def draw_collection(collection_name, __entry__=None):
    """ Generate Dependency Graph for all entries in the collection.   
    """
    collection_entry = __entry__.get_kernel().byname(collection_name)
    #print("collection_entry: ", collection_entry)
    if collection_name!=None:
        collection_path = collection_entry.get_path()
        #print("collection_path: ", collection_path)
        draw(collection_name, return_this_entry=collection_entry, __entry__=collection_entry)
        image_path = f'{collection_path}/image.png'
        dot_file_path = f'{collection_path}/image'
        print("image_path: ", image_path)
        print("dot_file_path: ", dot_file_path)
        try:
        # Construct the graph-easy command
            cmd = ['graph-easy', dot_file_path]
        
        # Run the command and capture the output
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check if the command was successful
            if result.returncode == 0:
                print("Graph-Easy output:")
                print(result.stdout)  # Print the graph-easy output
            else:
                print(f"Graph-Easy failed with error code {result.returncode}")
                print(result.stderr)  # Print any errors that occurred

        except FileNotFoundError:
            print("graph-easy command not found. Please ensure it is installed.")
        except Exception as e:
            print(f"An error occurred: {e}")

        return collection_entry

def print_hierarchy(entry_name, __entry__, indent_level=0, d=None, output=False):
    """
    Recursive function to print the entry, parent hierarchy in a tree-like structure with max_depth 'd'.

    Usage examples:
        axs byname hierarchy, print_hierarchy llmcb_using_qaic_kilt
        
    """
    entry = __entry__.get_kernel().byname(entry_name)
    
    if not entry:
        print("Entry not found!")
        return
    
    else:
        data = entry.own_data()
        # Collect all output-related fields
        output_entries_fields = [key for key in data.keys() if key.startswith("output_entry_parents_")]
        
        output_entries = {}
        for field in output_entries_fields:
            output_entries[field] = entry.get(field)
    
        for key, val in data.items():
            if "_parent_entries" in str(val):
                output = True
            elif "tags" in str(val):
                output = True
            elif output_entries:
                output = True

        byname_entries = set() # For now, only unique parent entries are kept in the set
        if output_entries:
            for field, output_entries_list in output_entries.items():
                print(f"output_entries_list: {output_entries_list}")
                byname_entries.update(extract_byname_entries(output_entries_list))
                print(byname_entries)
                
        
        base_indent = "    " * indent_level
        output_indent = "--> " * indent_level if output_entries else base_indent

        if d is not None and indent_level >= d:
            return

        print(f"{base_indent}{entry_name}")

        parents = entry.get("_parent_entries")
        
        # If there are parents, recursively print them
        if parents:
            for parent in parents:
                parent_name = parent if isinstance(parent, str) else parent.get_name()
                print(f"{base_indent}|")
                print(f"{base_indent}+-{parent.get_path()}")
                print_hierarchy(parent_name, __entry__, indent_level + 1, d=d)
        
        

        # If there are outputs, print their hierarchy
        if output:
                if output_entries:
                    for entry in byname_entries:
                        output_name = entry if isinstance(entry, str) else entry.get_name()
                        output_entry = __entry__.get_kernel().byname(entry)
                        print(f"{output_indent}|")
                        print(f"{output_indent}-->{output_entry.get_path()} --> Output Parents")
                        print_hierarchy(output_name, __entry__, indent_level + 1, d=d, output=True)
    
    return "Tree printed successfully!" 
