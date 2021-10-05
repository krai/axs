#!/usr/bin/env python3

""" This entry knows how to extract files from a given archive.
"""

import os

def extract(archive_path, entry_name, tags=None, __entry__=None):
    """Create a new entry and extract the archive into it

Usage examples:
    # Downloading the archive tarball:
            axs byname downloader , download 'http://cKnowledge.org/ai/data/ILSVRC2012_img_val_500.tar' tarball_imagenet ILSVRC2012_img_val_500.tar
    # Extracting the archive from one entry into another entry:
            axs byquery downloaded,file_name=ILSVRC2012_img_val_500.tar , archive_path: get_path , byname extractor , extract --entry_name=extracted_imagenet
    # Resulting entry path (counter-intuitively) :
            axs byname extracted_imagenet , get_path ''
    # Path to the directory with the extracted archive:
            axs byname extracted_imagenet , get_path
    # Clean up:
            axs byname extracted_imagenet , remove
            axs byname tarball_imagenet , remove
    """

    assert __entry__ != None, "__entry__ should be defined"

    dep_name        = 'extraction_tool'
    tool_entry      = __entry__[dep_name]
    tool_path       = tool_entry['tool_path']
    file_name       = 'extracted'

    if tool_path:

        result_data = {
            "archive_path": archive_path,
            "file_name":    file_name,
            "tool_path":    tool_path,
            "tags":         tags or [ "extracted" ],
        }

        result_entry    = __entry__.get_kernel().work_collection().call('attached_entry', deterministic=False).own_data( result_data ).save( entry_name )
        target_path     = result_entry.get_path(file_name)

        os.makedirs( target_path )

        print(f"Dependency '{dep_name}' resolved into entry '{tool_entry.get_path()}' with the tool '{tool_path}', it will be used for extracting")
        retval = tool_entry.call('run', [], {"tool_path": tool_path, "archive_path": archive_path, "target_path": target_path})
        if retval == 0:
            return target_path
        else:
            print(f"Some problem occured when trying to extract '{archive_path}' into '{target_path}', bailing out")
            result_entry.remove()
            return None
    else:
        print(f"Could not find a suitable extractor, so failed to extract {archive_path}")
        return None
