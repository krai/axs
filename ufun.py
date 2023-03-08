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


def fs_find(top_dir, regex, looking_for_dir=False, return_full=False, topdown=True):
    """Find a file or directory by regex in top_dir, return the list of all matches. Note: it must be Python's regex, not Shell's!

Usage examples :
                axs byquery extracted,imagenet , get_path ,0 func ufun.fs_find 'ILSVRC2012_val_\d+.JPEG' , __getitem__ 0
    """
    import os
    import re

    containing_subdirs = []
    for dirpath,dirnames,filenames in os.walk(top_dir, topdown=topdown):
        candidate_list = dirnames if looking_for_dir else filenames
        for candidate_name in candidate_list:
            if re.match(regex, candidate_name):
                containing_subdirs.append( os.path.join(dirpath, candidate_name) if return_full else dirpath )
                break

    return containing_subdirs


def join_with(things, separator=' '):
    """Reverse the order of arguments for String.join() to simplify its use in pipelines

Usage examples :
                axs work_collection , get contained_entries , keys ,0 func ufun.join_with
    """

    return separator.join(things)
