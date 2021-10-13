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

def download(url, file_name, tool_entry, tags=None, entry_name=None, __record_entry__=None):
    """Create a new entry and download the url into it

Usage examples:
    # Manual downloading into a new entry:
            axs byname downloader , download 'https://example.com/' example.html --entry_name=examplepage_downloaded
    # Resulting entry path (counter-intuitively) :
            axs byquery downloaded,file_name=example.html , get_path ''
    # Downloaded file path:
            axs byquery downloaded,file_name=example.html , get_path
    # Reaching to the original tool used for downloading:
            axs byquery downloaded,file_name=example.html , get tool_entry , get tool_path
    # Clean up:
            axs byquery downloaded,file_name=example.html , remove
    """

    __record_entry__["tags"] = tags or ["downloaded"]
    __record_entry__.save( entry_name )
    target_path     = __record_entry__.get_path(file_name)

    print(f"The resolved tool_entry '{tool_entry.get_name()}' located at '{tool_entry.get_path()}' uses the shell tool '{tool_entry['tool_path']}'")
    retval = tool_entry.call('run', [], {"url": url, "target_path": target_path})
    if retval == 0:
        return target_path
    else:
        print(f"A problem occured when trying to download '{url}' into '{target_path}', bailing out")
        __record_entry__.remove()
        return None
