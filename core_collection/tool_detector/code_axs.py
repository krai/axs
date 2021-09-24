#!/usr/bin/env python3

""" This entry knows how to detect and set up shell tools
"""


def detect(tool_name, tool_name2extra_params, __entry__=None):
    """Detect an installed shell tool and create an entry to point at it

Usage examples :
                axs byname tool_detector , detect wget

                axs byname tool_detector , detect curl
    """

    assert __entry__ != None, "__entry__ should be defined"

    tool_path   = __entry__.call('which', tool_name)

    if tool_path:
        tool_name2extra_params  = tool_name2extra_params or {}

        result_data = {
            "_parent_entries":  [ [ "^", "byname", "shell" ] ],
            "tool_name":    tool_name,
            "tool_path":    tool_path,
            "shell_cmd":    tool_path,  # likely to be overridden by tool_name2extra_params[tool_name]
            "tags":         [ "shell_tool" ],
        }
        result_data.update( tool_name2extra_params.get(tool_name, {}) )

        ak = __entry__.get_kernel()
        assert ak != None, "__entry__'s kernel should be defined"

        result_entry_name   = tool_name + '_tool'
        result_entry        = ak.fresh(own_data=result_data).save(ak.work_collection().get_path(result_entry_name)).attach()

        return result_entry
    else:
        print(f"Could not detect the tool '{tool_name}'")
        return None
