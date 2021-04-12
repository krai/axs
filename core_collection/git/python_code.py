#!/usr/bin/env python3

""" This entry knows how to download git repositories.
"""

import os

def pull(name=None, url=None, container_dir=None, __entry__=None):
    """Either clone a git repository if it didn't exist locally,
        or pull a git repository if it did exit.
        Note: it does not (yet) add the repository to any collection, it has to be done manually.

Usage examples :
            axs byname git , pull counting_collection
            axs work_collection , plant contained_entries.counting_collection counting_collection , save
    """

    assert __entry__ != None, "__entry__ should be defined"
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"

    if url:
        if name==None:
            name = os.path.basename( url )
            if name.endswith('.git'):
                name = name[:-4]        # trim it off
    elif name:
        __entry__["name"] = name
        url = __entry__["url"]          # use this Entry's substitution mechanism

    print(f"axs-git-pull: name={name}, url={url}")

    repo_entry  = ak.bypath(name) if name else __entry__
    repo_path   = repo_entry.get_path()

    if os.path.exists( repo_path ):
        shell_cmd = f"git -C {repo_path} pull"
    else:
        shell_cmd = f"git clone {url}"

    print(f"Running command: {shell_cmd}")

    __entry__.call('run', [shell_cmd])
