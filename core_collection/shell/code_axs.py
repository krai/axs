#!/usr/bin/env python3

""" This entry knows how to run an arbitrary shell command in a given environment
    and optionally capture the output.
"""

import logging
import os
import subprocess
import sys

def run(shell_cmd, env=None, capture_output=False, split_to_lines=False):
    """Run the given shell command in the given environment

Usage examples:
            axs byname shell , run 'echo This is a test.'

    # dynamically create a tool and use it:
            axs fresh , plant _parent_entries --,:=AS^IS:^:byname:shell , plant tool_path --:=^^:which:wget , plant shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' , run --url=https://example.com --target_path=example.html

    # first create a downloading tool, then use it:
            axs fresh ---own_data='{"_parent_entries":[["AS^IS","^","byname","shell"]]}' , plant tool_name wget tool_path --:=^^:which:wget shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' tags --,=shell_tool,can_download_url , save wget_tool
            axs bypath wget_tool , run --url=https://example.com --target_path=example.html

    """
    env = env or {}
    if env:
        shell_cmd = 'env ' + ' '.join([ f"{k}={env[k]}" for k in env]) + ' ' + shell_cmd

    logging.warning("shell.run() about to execute:\n\t{shell_cmd}\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    completed_process = subprocess.run(shell_cmd, shell = True, stdout=(subprocess.PIPE if capture_output else None) )
    if capture_output:
        output  = completed_process.stdout.decode('utf-8').rstrip()

        if split_to_lines:
            output = output.split('\n')

        return output
    else:
        return completed_process.returncode


def under_win():
    """Fast way to check if we are running under any of Windows-derived OS

Usage examples:
            axs byname shell , under_win
    """
    return sys.platform.startswith('win')


def which(exec_name, env=None):
    """OS-independent routine to search for an executable in the OS's executable path.

Usage examples:
            axs byname shell , which wget
    """
    exec_dirs   = os.get_exec_path(env)
    suffixes    = ('', '.exe', '.bat', '.com') if under_win() else ('',)

    for exec_dir in exec_dirs:
        for suffix in suffixes:
            candidate_full_path = os.path.join(exec_dir, exec_name + suffix)
            if os.access(candidate_full_path, os.X_OK):
                return candidate_full_path
    return None


if __name__ == '__main__':

    # When the entry's code is run as a script, perform local tests:
    #
    return_code = run( "echo Hello, world!" )
    print(f"ReturnCode = {return_code}\n")

    return_code = run( shell_cmd='env', env={'FOO':12345, 'BAR':23456, 'BAZ':34567} )
    print(f"ReturnCode = {return_code}\n")
