import json
import os

base_directory = os.path.expanduser('~/axs/core_collection/workflows_collection')

def get_contained_entries_keys_from_multiple_locations():
    folders = ['bert', 'image_classification', 'object_detection']
    keys_dict = {}
    workflows_directory = os.path.expanduser('~/axs/core_collection/workflows_collection')
    
    for folder in folders:
        for root, dirs, files in os.walk(os.path.join(workflows_directory, folder)):
            if 'data_axs.json' in files:
                json_file_path = os.path.join(root, 'data_axs.json')
                
                print(f"Checking existence of {json_file_path}")  # Debug line
                
                with open(json_file_path, 'r') as f:
                    data = json.load(f)
                    keys = list(data.get('contained_entries', {}).keys())
                    
                    if folder in keys_dict:
                        keys_dict[folder].extend(keys)
                    else:
                        keys_dict[folder] = keys
            else:
                print(f"The JSON file at {os.path.join(root, 'data_axs.json')} doesn't exist.")
    
    return keys_dict

contained_entries_keys_dict = get_contained_entries_keys_from_multiple_locations()

key_json_paths = []

for folder, keys in contained_entries_keys_dict.items():
    for key in keys:
        key_json_path = os.path.join(base_directory,folder, key, 'data_axs.json')
        key_json_paths.append(key_json_path)

def read_entries(key_json_paths, entry_key):
    entries_dict = {}
    for key_json_path in key_json_paths:
        if os.path.exists(key_json_path):
            with open(key_json_path, 'r') as f:
                data = json.load(f)
            key_name = os.path.basename(os.path.dirname(key_json_path))
            entries_dict[key_name] = [entry[-1] for entry in data.get('_parent_entries', [])]
        else:
            print(f"The JSON file at {key_json_path} doesn't exist.")
    return entries_dict

# Read parent entries
parent_entries_dict = read_entries(key_json_paths, '_parent_entries')

def read_output_parent_entries(key_json_paths):
    output_parent_entries_dict = {}
    for key_json_path in key_json_paths:
        if os.path.exists(key_json_path):
            with open(key_json_path, 'r') as f:
                data = json.load(f)
            output_key_name = os.path.basename(os.path.dirname(key_json_path))

            final_entries = []
            for entry in data.get('output_entry_parents', []):
                if isinstance(entry, list) and 'byname' in entry:
                    index = entry.index('byname') + 1
                    if index < len(entry):
                        final_entries.append(entry[index])
            
            if final_entries:
                output_parent_entries_dict[output_key_name] = final_entries
            else:
                output_parent_entries_dict[output_key_name] = data.get('output_entry_parents', [])

        else:
            print(f"The JSON file at {key_json_path} doesn't exist.")
    
    return output_parent_entries_dict

# Read output parent entries
output_parent_entries_dict = read_output_parent_entries(key_json_paths)

# Save to a JSON file
with open('parent_entries_dict.json', 'w') as f:
    json.dump(parent_entries_dict, f, indent=4)

with open('output_parent_entries_dict.json', 'w') as f:
    json.dump(output_parent_entries_dict, f, indent=4)
