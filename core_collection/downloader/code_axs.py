#!/usr/bin/env python3

""" This entry knows how to download a file from a given URL.
    The resulting file may either become a collection or a regular entry.

Creating a recipe entry:
    axs work_collection , attached_entry examplepage_recipe , plant url http://example.com/  entry_name examplepage_downloaded  file_name example.html  _parent_entries --,:=AS^IS:^:byname:downloader , save

Activating the recipe, performing the actual downloading:
    axs byname examplepage_recipe , download

Getting the path to the downloaded file:
    cat `axs byname examplepage_downloaded , get_path`

Cleaning up:
    axs byname examplepage_downloaded , remove
    axs byname examplepage_recipe , remove

"""

import logging


def download(url, file_name=None, md5=None, downloading_tool_entry=None, md5_tool_entry=None, tags=None, entry_name=None, __record_entry__=None):
    """Create a new entry and download the url into it

Usage examples:
    # Manual downloading into a new entry:
            axs byname downloader , download 'https://example.com/' example.html --tags,=downloaded,example
    # Replay of the same command at a later time, stored in a different entry:
            axs byquery downloaded,file_name=example.html , get _replay --entry_name=replay_downloading_example.html
    # Resulting entry path (counter-intuitively) :
            axs byquery downloaded,file_name=example.html , get_path ''
    # Downloaded file path:
            axs byquery downloaded,file_name=example.html , get_path
    # Reaching to the original tool used for downloading:
            axs byquery downloaded,file_name=example.html , get downloading_tool_entry , get tool_path
    # Clean up:
            axs byquery downloaded,file_name=example.html , remove
    """

    if not file_name:
        import os
        file_name = os.path.basename(url)
        __record_entry__["file_name"] = file_name

    if not entry_name:
        entry_name = 'generated_by_downloading_' + file_name

    __record_entry__.pluck("entry_name")

    __record_entry__["tags"] = tags or ["downloaded"]
    __record_entry__.save( entry_name )
    target_path     = __record_entry__.get_path(file_name)

    logging.warning(f"The resolved downloading_tool_entry '{downloading_tool_entry.get_name()}' located at '{downloading_tool_entry.get_path()}' uses the shell tool '{downloading_tool_entry['tool_path']}'")
    retval = downloading_tool_entry.call('run', [], {"url": url, "target_path": target_path})
    if retval == 0:
        if md5 is not None:
            logging.warning(f"The resolved md5_tool_entry '{md5_tool_entry.get_name()}' located at '{md5_tool_entry.get_path()}' uses the shell tool '{md5_tool_entry['tool_path']}'")
            computed_md5 = md5_tool_entry.call('run', [], {"file_path": target_path})
            if computed_md5 != md5:
                logging.error(f"The computed md5 sum '{computed_md5}' is different from the expected '{md5}', bailing out")
                __record_entry__.remove()
                return None
            else:
                logging.warning(f"The computed md5 sum '{computed_md5}' matched the expected one.")

        return __record_entry__
    else:
        logging.error(f"A problem occured when trying to download '{url}' into '{target_path}', bailing out")
        __record_entry__.remove()
        return None
