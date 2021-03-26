#!/usr/bin/env python3

""" Example entry that is not a part of any collection.

    This entry knows how to run an arbitrary command in a given environment.
"""

import subprocess

def run(shell_cmd, env=None):
    """ Run the given shell command in the given environment

        Usage example:
            axs shell run 'echo This is a test.'
    """

    env = env or {}

    env_setting_prefix = 'env ' + ' '.join([ f"{k}={env[k]}" for k in env])
    if env_setting_prefix:
        shell_cmd = env_setting_prefix + ' ' + shell_cmd

    return_code = subprocess.call(shell_cmd, shell = True)

    return return_code



if __name__ == '__main__':

    # When the entry's code is run as a script, perform local tests:
    #
    return_code = run( "echo Hello, world!" )
    print(f"ReturnCode = {return_code}\n")

    return_code = run( shell_cmd='env', env={'FOO':12345, 'BAR':23456, 'BAZ':34567} )
    print(f"ReturnCode = {return_code}\n")
