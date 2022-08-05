#!/usr/bin/env python3

""" This entry knows how to download git repositories.
    They may either become collections or regular entries.
"""

import os


def url_2_repo_name(url=None):
    """Cut the repo_name out of the URL, if given.

Usage examples :
                axs byname git , get repo_name --url=https://hello.world/repo/long_name.git
                axs byname git , get url --repo_name=short_name
    """
    if url:
        repo_name = os.path.basename( url )
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]          # trim it off

        return repo_name
    else:
        return None


def clone(repo_name=None, url=None, git_tool_entry=None, container_entry=None, checkout=None, submodules=False, tags=None, __entry__=None):
    """Clone a git repository into an Entry,

Usage examples :
                axs byname git , clone --repo_name=counting_collection
            # or
                axs byname git , clone --url=https://github.com/user_x/counting_collection
            # or
                axs byquery git_repo,repo_name=counting_collection
Clean-up:
                axs byname counting_collection , remove
    """

    assert __entry__ != None, "__entry__ should be defined"
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"

    container_path  = container_entry.get_path('')
    entry_path      = container_entry.get_path( repo_name )
    tool_path       = git_tool_entry["tool_path"]
    git_tool_entry.call('run', f"\"{tool_path}\" -C \"{container_path}\" clone {url} {repo_name}" )

    if checkout:
        git_tool_entry.call('run', f"\"{tool_path}\" -C \"{entry_path}\" checkout \"{checkout}\"" )

    if submodules:
        git_tool_entry.call('run', f"\"{tool_path}\" -C \"{entry_path}\" submodule init" )
        git_tool_entry.call('run', f"\"{tool_path}\" -C \"{entry_path}\" submodule update" )

    result_entry                = ak.bypath( entry_path )   # "discover" the Entry after cloning, then either create or augment the data
    result_entry['repo_name']   = repo_name
    result_entry['tags']        = tags or [ 'git_repo' ]
    result_entry.attach( container_entry ).save()

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
