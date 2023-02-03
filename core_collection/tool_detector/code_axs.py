#!/usr/bin/env python3

""" This entry knows how to detect and set up shell tools
"""

import logging
import os
import sys


def which(tool_name, exec_suffixes=None, env=None):
    """OS-independent routine to search for an executable in the OS's executable path.

Usage examples:
            axs byname tool_detector , which wget
    """
    exec_dirs   = os.get_exec_path(env)

    for exec_dir in exec_dirs:
        for suffix in exec_suffixes:
            candidate_full_path = os.path.join(exec_dir, tool_name + suffix)
            if os.access(candidate_full_path, os.X_OK):
                return candidate_full_path
    return None


def detect(tool_name=None, tool_path=None, tags=None, entry_name=None, parent_entry_name="shell", __record_entry__=None):
    """Detect/select an installed shell tool and create an entry to point at it

Usage examples :
                axs byname tool_detector , detect wget --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#'

                axs byname tool_detector , detect curl --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -L -o #{target_path}# #{url}#'

                axs byquery shell_tool,can_python                       # select kernel_python by default

                axs byquery shell_tool,can_python,tool_name=python3.8   # detect a custom tool_name

                axs byquery shell_tool,can_download_url , run --url=https://example.com/ --target_path=example.html
    """

    if tool_path:
        __record_entry__["tool_path"]       = tool_path
        __record_entry__["_parent_entries"] = [ [ "^", "byname", parent_entry_name ] ]
        __record_entry__.parent_objects     = None      # reload parents

        if not entry_name:
            entry_name      = tool_name + '_tool'

        __record_entry__.pluck("entry_name")

        __record_entry__["tags"] = tags or ["shell_tool"]
        __record_entry__.save( entry_name )

        return __record_entry__
    else:
        logging.warning(f"Could not detect the tool '{tool_name}'")
        return None
