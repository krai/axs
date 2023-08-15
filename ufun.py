#!/usr/bin/env python3

"A collection of utility functions"

import errno
import json
import os
import re
import shutil
import stat
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
    searchObj = re.search(regex, input_string)
    if searchObj:
        if group>0:
            return searchObj.group(group)
        else:
            return True
    else:
        print(f'Failed to match "{input_string}" against "{regex}"', file=sys.stderr)
        return False


def fs_find(top_dir, regex, looking_for_dir=False, return_full=False, topdown=True):
    """Find a file or directory by regex in top_dir, return the list of all matches. Note: it must be Python's regex, not Shell's!

Usage examples :
                axs byquery extracted,imagenet , get_path ,0 func ufun.fs_find 'ILSVRC2012_val_\d+.JPEG' , __getitem__ 0
    """
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
                axs noop --,=ab,cd,ef ,0 func ufun.join_with $'\n'      # note Bash-specific syntax for passing a carriage return
    """
    return separator.join(things)


def rmdir(dir_path):
    """Recursively remove a non-empty directory

Usage examples :
                axs func ufun.rmdir path/to/remove
    """
    #   Thanks for this SO entry:
    #       https://stackoverflow.com/questions/1213706/what-user-do-python-scripts-run-as-in-windows
    #
    def handleRemoveReadonly(func, path, exc):
        if func in (os.rmdir, os.remove) and exc[1].errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # 0777
            func(path)
        else:
            raise

    shutil.rmtree(dir_path, ignore_errors=False, onerror=handleRemoveReadonly)


def is_in(candidate, iterable):
    """Check if element is TRULY contained in the iterable.

Note that the following are true in Python:
    1==True
    0==False
    True in [1]
    1 in [True]
    False in [0]
    0 in [False]

So to account for the difference between (1 and True) and between (0 and False), we employ or own containment check.

Usage examples :
                axs func ufun.is_in 0 ---='[false,2,4]'
                axs func ufun.is_in --- ---='[false,2,4]'
                axs func ufun.is_in 1 ---='[0,true,4]'
                axs func ufun.is_in --+ ---='[0,true,4]'
    """
    for element in iterable:
        if candidate is element:
            return True
    return False
