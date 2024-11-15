#!/usr/bin/env python3

""" This entry knows how to run an arbitrary shell command in a given environment
    and optionally capture the output.
"""

import logging
import os
import subprocess
import sys


def subst_run(template, __entry__=None, **rest):
    """Substitute data into a given template and run the resulting shell command in the given environment

Usage examples:
                axs .shell.subst_run 'echo #{greetings}#, #{name}#' --greetings=Hello --name=World

    # execute a shell command in a specific directory:
                axs wp: .work_collection.get_path , .shell.subst_run 'ls -l #{wp}#'
    """
    return __entry__.call( 'run', __entry__.substitute(template) )


def run(shell_cmd, in_dir=None, env=None, capture_output=False, errorize_output=False, capture_stderr=False, suppress_stderr=False, split_to_lines=False, return_saved_record_entry=False, return_this_entry=None, get_and_return_on_success=None, n_attempts=1, __entry__=None, __record_entry__=None):
    """Run the given shell command in the given environment

Usage examples:
                axs byname shell , run 'echo This is a test.'

    # dynamically create a tool and use it:
                axs fresh_entry , plant _parent_entries --,:=AS^IS:^:byname:shell , plant tool_path --:=^^:which:wget , plant shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' , run --url=https://example.com --target_path=example.html

    # first create a downloading tool, then use it:
                axs fresh_entry ---own_data='{"_parent_entries":[["AS^IS","^","byname","shell"]]}' , plant tool_name wget tool_path --:=^^:which:wget shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' tags --,=shell_tool,can_download_url , save wget_tool
                axs bypath wget_tool , run --url=https://example.com --target_path=example.html

    # run an interactive shell inside a given entry:
                axs byname axs2mlperf , get_path ,1 .shell.run bash
    """
    if type(shell_cmd)==list:   # making sure all components are strings
        shell_cmd = [str(x) for x in shell_cmd]


    if in_dir:
        prev_dir = os.getcwd()
        os.chdir( in_dir )

    if capture_output:
        stdout_target = subprocess.PIPE
    elif errorize_output:
        stdout_target = sys.stderr.buffer
    else:
        stdout_target = None

    if capture_stderr:
        stderr_target = subprocess.PIPE
    elif suppress_stderr:
        stderr_target = subprocess.DEVNULL
    else:
        stderr_target = None

    if env:
        env = { k: str(env[k]) for k in env }   # cast all env's values to strings

    while n_attempts:
        logging.warning(f"shell.run() about to execute (with in_dir={in_dir}, env={env}, capture_output={capture_output}, errorize_output={errorize_output}, capture_stderr={capture_stderr}, split_to_lines={split_to_lines}):\n\t{shell_cmd}\n" + (' '*8 + '^'*len(shell_cmd)) )

        completed_process = subprocess.run(shell_cmd, shell = (type(shell_cmd)!=list), env=env, stdout=stdout_target, stderr=stderr_target)
        if completed_process.returncode==0:
            break
        else:
            n_attempts-=1
            logging.warning(f"shell.run() failed with return code {completed_process.returncode}, {n_attempts} remaining")

    if in_dir:
        os.chdir( prev_dir )

    if capture_output or capture_stderr:    # FIXME: assuming XOR at the moment
        output  = (completed_process.stderr if capture_stderr else completed_process.stdout).decode('utf-8').rstrip()

        if split_to_lines:
            output = output.split('\n')

        return output
    elif return_saved_record_entry:
        return __record_entry__.save()
    elif return_this_entry:
        return return_this_entry
    elif get_and_return_on_success and not completed_process.returncode:
        return __entry__[get_and_return_on_success]
    else:
        return completed_process.returncode


if __name__ == '__main__':

    # When the entry's code is run as a script, perform local tests:
    #
    return_code = run( "echo Hello, world!" )
    print(f"ReturnCode = {return_code}\n")

    return_code = run( shell_cmd='env', env={'FOO':12345, 'BAR':23456, 'BAZ':34567} )
    print(f"ReturnCode = {return_code}\n")
