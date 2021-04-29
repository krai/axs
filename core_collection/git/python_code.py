#!/usr/bin/env python3

""" This entry knows how to download git repositories.
    They may either become collections or regular entries.
"""

import os

def pull(name=None, url=None, __entry__=None):
    """Either clone a git repository if it didn't exist locally,
        or pull a git repository if it did exit.
        Note: it does not (yet) add the repository to any collection, it has to be done manually.

Usage examples :
            axs byname git , pull counting_collection , attach

            axs byname counting_collection , pull
Clean-up:
            axs byname counting_collection , remove
    """

    assert __entry__ != None, "__entry__ should be defined"
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"

    if url:
        if name==None:
            name = os.path.basename( url )
            if name.endswith('.git'):
                name = name[:-4]        # trim it off
        clone = True
    elif name:
        __entry__["name"] = name
        url = __entry__["url"]          # use this Entry's substitution mechanism
        clone = True
    else:
        clone = False


    if clone:
        work_collection = ak.work_collection()
        container_path  = work_collection.get_path('')
        __entry__.call('run', f"git -C {container_path} clone {url}" )
        repo_entry      = work_collection.bypath(name)
    else:
        repo_entry      = __entry__
        repo_path       = repo_entry.get_path()
        __entry__.call('run',  f"git -C {repo_path} pull --ff-only" )

    return repo_entry
