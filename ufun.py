#!/usr/bin/env python3

"A collection of utility functions"

import json
import sys

def load_json(json_file_path):
    """Load a data structure from given JSON file.

Usage examples :
                axs func ufun.load_json ab.json , keys ,0 func list
                axs byquery program_output,detected_coco,framework=onnx,model_name=ssd_resnet34,num_of_images=5 , get_path_from output_file_name ,0 func ufun.load_json
    """
    with open( json_file_path, encoding='utf-8' ) as json_fd:
        try:
            data_structure = json.load(json_fd)
        except json.decoder.JSONDecodeError as e:
            print(f'Error parsing "{json_file_path}" : {e}', file=sys.stderr)
            data_structure = {}

        return data_structure


def save_json(data_structure, json_file_path, indent=None):
    """Store a data structure in a JSON file.

Usage examples :
                axs func ufun.save_json ---='{"hello":"world"}' hello.json
                axs work_collection , get contained_entries , keys ,0 func list ,0 func ufun.save_json work_entries.json
    """

    json_string   = json.dumps( data_structure , indent=indent)

    with open(json_file_path, "w") as json_fd:
        json_fd.write( json_string+"\n" )

    return json_string


def rematch(input_string, regex, group=1):
    """Find a substring matching a given regular expression and return it

Usage examples :
                axs byname kernel_python_tool , run ,0 func ufun.rematch '^Python\s((\d+)\.(\d+))\.\d+'    # parse the major.minor version from Python
    """
    import re

    searchObj = re.search(regex, input_string)
    if searchObj:
        if group>0:
            return searchObj.group(group)
        else:
            return True
    else:
        return False

