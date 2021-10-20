#!/usr/bin/env python3

""" This entry knows how to extract files from a given archive.
"""

import logging
import os


def extract(archive_path, tool_entry, file_name="extracted", tags=None, entry_name=None, __record_entry__=None):
    """Create a new entry and extract the archive into it

Usage examples:
    # Downloading the archive tarball:
            axs byname downloader , download 'http://cKnowledge.org/ai/data/ILSVRC2012_img_val_500.tar'
        # or
            axs byname downloader , call '--pos_params,=http://cKnowledge.org/ai/data/ILSVRC2012_img_val_500.tar'
    # Extracting the archive from one entry into another entry:
            axs byquery downloaded,file_name=ILSVRC2012_img_val_500.tar , archive_path: get_path , byname extractor , extract
    # Resulting entry path (counter-intuitively) :
            axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar , get_path ''
    # Path to the directory with the extracted archive:
            axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar , get_path
    # Clean up:
            axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar --- , remove
            axs byquery downloaded,file_name=ILSVRC2012_img_val_500.tar --- , remove
    """

    __record_entry__["tags"] = tags or ["extracted"]

    import os
    archive_name    = os.path.basename(archive_path)
    __record_entry__["archive_name"] = archive_name

    if not entry_name:
        entry_name = 'generated_by_extracting_' + archive_name

    __record_entry__.save( entry_name )
    target_path     = __record_entry__.get_path(file_name)

    os.makedirs( target_path )

    logging.warning(f"The resolved tool_entry '{tool_entry.get_name()}' located at '{tool_entry.get_path()}' uses the shell tool '{tool_entry['tool_path']}'")
    retval = tool_entry.call('run', [], {"archive_path": archive_path, "target_path": target_path})
    if retval == 0:
        return target_path
    else:
        logging.error(f"A problem occured when trying to extract '{archive_path}' into '{target_path}', bailing out")
        __record_entry__.remove()
        return None
