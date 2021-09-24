#!/usr/bin/env python3

""" This entry knows how to download a file from a given URL.
    The resulting file may either become a collection or a regular entry.

Creating a recipe entry:
    axs fresh , plant url http://example.com/ , plant entry_name examplepage_downloaded , plant file_name example.html , plant _parent_entries,:=^:byname:downloader , save examplepage_recipe , attach

Activating the recipe, performing the actual downloading:
    axs byname examplepage_recipe , download

Getting the path to the downloaded file:
    cat `axs byname examplepage_downloaded , get_path`

Cleaning up:
    axs byname examplepage_downloaded , remove
    axs byname examplepage_recipe , remove


"""

def download(url, entry_name, file_name, __entry__):
    """Create a new entry and download the url into it

Usage examples:
    # Installing executable tools:
            axs fresh ---own_data='{"_parent_entries":[["AS^IS","^","byname","shell"]]}' , plant tool_name wget tool_path --:=^^:which:wget shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' tags --,=shell_tool implements --,=url_download , save wget_tool , attach
            axs byquery shell_tool,tool_name=curl
    # Manual downloading into a new entry:
            axs byname downloader , download 'https://example.com' examplepage_downloaded example.html
    # Resulting entry path (counter-intuitively) :
            axs byname examplepage_downloaded , get_path ''
    # Downloaded file path:
            axs byname examplepage_downloaded , get_path
    # Reaching to the original producer (this Entry):
            axs byname examplepage_downloaded , get producer , get_path
    # Clean up:
            axs byname examplepage_downloaded , remove
    """

    dep_name        = 'url_download_tool'
    tool_entry      = __entry__[dep_name]
    tool_path       = tool_entry['tool_path']

    if tool_path:

        result_data = {
            "url":          url,
            "file_name":    file_name,
            "tool_path":    tool_path,
            "tags":         [ "downloaded" ],
        }

        ak              = __entry__.get_kernel()
        result_entry    = ak.fresh(own_data=result_data).save(ak.work_collection().get_path(entry_name)).attach()
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
