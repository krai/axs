#!/usr/bin/env python3

""" This entry knows how to detect and set up shell tools
"""

import logging

def detect(tool_name, shell_cmd=None, capture_output=None, tags=None, __entry__=None):
    """Detect an installed shell tool and create an entry to point at it

Usage examples :
                axs byname tool_detector , detect wget --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#'

                axs byname tool_detector , detect curl --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -o #{target_path}# #{url}#'
    """

    assert __entry__ != None, "__entry__ should be defined"

    tool_path   = __entry__.call('which', tool_name)

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

        ak = __entry__.get_kernel()
        assert ak != None, "__entry__'s kernel should be defined"

        result_entry_name   = tool_name + '_tool'
        result_entry        = ak.fresh(own_data=result_data).save(ak.work_collection().get_path(result_entry_name)).attach()

        return result_entry
    else:
        logging.warning(f"Could not detect the tool '{tool_name}'")
        return None
