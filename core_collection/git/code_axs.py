#!/usr/bin/env python3

""" This entry knows how to download git repositories.
    They may either become collections or regular entries.
"""

import os


def url_2_repo_name(url=None):
    """Cut the repo_name out of the URL, if given.

Usage examples :
                axs byname git , get name --url=https://hello.world/repo/long_name.git
                axs byname git , get url --name=short_name
    """
    if url:
        name = os.path.basename( url )
        if name.endswith('.git'):
            name = name[:-4]        # trim it off

        return name
    else:
        return None


def clone(name=None, url=None, git_tool_entry=None, tags=None, __entry__=None):
    """Clone a git repository into an Entry,

Usage examples :
                axs byname git , clone --name=counting_collection
            # or
                axs byname git , clone --url=https://github.com/user_x/counting_collection
            # or
                axs byquery git_repo,name=counting_collection
Clean-up:
                axs byname counting_collection , remove
    """

    assert __entry__ != None, "__entry__ should be defined"
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"

    work_collection = ak.work_collection()
    container_path  = work_collection.get_path('')
    tool_path       = git_tool_entry["tool_path"]
    git_tool_entry.call('run', f"\"{tool_path}\" -C \"{container_path}\" clone {url} {name}" )
    result_entry            = ak.bypath( work_collection.get_path(name) )
    result_entry['name']    = name
    result_entry['tags']    = tags or [ 'git_repo' ]
    result_entry.attach( work_collection ).save()

    return result_entry



def pull(repo_path, git_tool_entry, __entry__=None):
    """Pull the repository contained in an entry.

Usage examples :
                axs byname counting_collection , pull

                axs byname git , pull `axs core_collection , get_path`
    """
    tool_path       = git_tool_entry["tool_path"]
    git_tool_entry.call('run', f"\"{tool_path}\" -C \"{repo_path}\" pull --ff-only" )

    return __entry__
