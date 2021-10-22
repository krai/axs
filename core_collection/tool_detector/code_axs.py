#!/usr/bin/env python3

""" This entry knows how to detect and set up shell tools
"""

import logging
import os
import sys


def under_win():
    """Fast way to check if we are running under any of Windows-derived OS

Usage examples:
            axs byname tool_detector , under_win
    """
    return sys.platform.startswith('win')


def which(exec_name, env=None):
    """OS-independent routine to search for an executable in the OS's executable path.

Usage examples:
            axs byname tool_detector , which wget
    """
    exec_dirs   = os.get_exec_path(env)
    suffixes    = ('', '.exe', '.bat', '.com') if under_win() else ('',)

    for exec_dir in exec_dirs:
        for suffix in suffixes:
            candidate_full_path = os.path.join(exec_dir, exec_name + suffix)
            if os.access(candidate_full_path, os.X_OK):
                return candidate_full_path
    return None


def detect(tool_name, shell_cmd=None, capture_output=None, tags=None, __entry__=None):
    """Detect an installed shell tool and create an entry to point at it

Usage examples :
                axs byname tool_detector , detect wget --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#'

                axs byname tool_detector , detect curl --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -o #{target_path}# #{url}#'
    """

    assert __entry__ != None, "__entry__ should be defined"

    tool_path   = which(tool_name)

    if tool_path:
        shell_cmd   = shell_cmd or tool_path
        tags        = tags or []

        result_data = {
            "_parent_entries":  [ [ "^", "byname", "shell" ] ],
            "tool_name":    tool_name,
            "tool_path":    tool_path,
            "shell_cmd":    shell_cmd,
            "tags":         tags or [ "shell_tool" ],
        }

        if shell_cmd is not None:
            result_data["shell_cmd"] = shell_cmd
        if capture_output is not None:
            result_data["capture_output"] = capture_output

        entry_name      = tool_name + '_tool'
        result_entry    = __entry__.get_kernel().work_collection().call('attached_entry', deterministic=False).own_data( result_data ).save( entry_name )

        return result_entry
    else:
        logging.warning(f"Could not detect the tool '{tool_name}'")
        return None
