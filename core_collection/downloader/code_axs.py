#!/usr/bin/env python3

""" This entry knows how to download a file from a given URL.
    The resulting file may either become a collection or a regular entry.

Creating a recipe entry:
    axs work_collection , attached_entry examplepage_recipe , plant url http://example.com/  entry_name examplepage_downloaded  file_name example.html  _parent_entries,:=^:byname:downloader , save

Activating the recipe, performing the actual downloading:
    axs byname examplepage_recipe , download

Getting the path to the downloaded file:
    cat `axs byname examplepage_downloaded , get_path`

Cleaning up:
    axs byname examplepage_downloaded , remove
    axs byname examplepage_recipe , remove


"""

def download(url, entry_name, file_name, tags=None, __entry__=None):
    """Create a new entry and download the url into it

Usage examples:
    # Manual downloading into a new entry:
            axs byname downloader , download 'https://example.com' examplepage_downloaded example.html
    # Resulting entry path (counter-intuitively) :
            axs byname examplepage_downloaded , get_path ''
    # Downloaded file path:
            axs byname examplepage_downloaded , get_path
    # Reaching to the original tool used for downloading:
            axs byname examplepage_downloaded , get tool_path
    # Clean up:
            axs byname examplepage_downloaded , remove
    """

    assert __entry__ != None, "__entry__ should be defined"

    dep_name        = 'url_download_tool'
    tool_entry      = __entry__[dep_name]
    tool_path       = tool_entry['tool_path']

    if tool_path:

        result_data = {
            "url":          url,
            "file_name":    file_name,
            "tool_path":    tool_path,
            "tags":         tags or [ "downloaded" ],
        }

        result_entry    = __entry__.get_kernel().work_collection().call('attached_entry', deterministic=False).own_data( result_data ).save( entry_name )
        target_path     = result_entry.get_path(file_name)

        print(f"Dependency '{dep_name}' resolved into entry '{tool_entry.get_path()}' with the tool '{tool_path}', it will be used for downloading")
        retval = tool_entry.call('run', [], {"url": url, "target_path": target_path})
        if retval == 0:
            return target_path
        else:
            print(f"Some problem occured when trying to download '{url}' into '{target_path}', bailing out")
            result_entry.remove()
            return None
    else:
        print(f"Could not find a suitable downloader, so failed to download {url}")
        return None
