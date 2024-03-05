#!/usr/bin/env python3

""" This entry knows how to extract files from a given archive.
"""

import logging
import os

def detect_archive_format(archive_path):
    if archive_path.lower().endswith('.tar'):
        archive_format = 'tar'
    elif archive_path.lower().endswith( ('.tgz','.tar.gz') ):
        archive_format = 'tgz'
    elif archive_path.lower().endswith('.zip'):
        archive_format = 'zip'
    elif archive_path.lower().endswith('.tar.xz'):
        archive_format = 'txz'
    return archive_format


def extract(archive_path, abs_install_dir, stored_newborn_entry, extraction_tool_entry, archive_format, strip_components=0):
    """Create a new entry and extract the archive into it

Usage examples:
    # Extracting an arbitrary tarball (zipped or otherwise) into an Entry:
            axs byname extractor , extract two_points.tar
            axs byname extractor , extract --archive_path=/datasets/dataset-imagenet-ilsvrc2012-val.tar --tags,=imagenet50k --strip_components=1

    # Downloading the archive tarball:
            axs byname downloader , download 'http://cKnowledge.org/ai/data/ILSVRC2012_img_val_500.tar'
        # or
            axs byname downloader , call "--url=http://cKnowledge.org/ai/data/ILSVRC2012_img_val_500.tar"
    # Extracting the archive from one entry into another entry:
            axs byquery downloaded,file_name=ILSVRC2012_img_val_500.tar , archive_path: get_path , byname extractor , extract
    # Resulting entry path (counter-intuitively) :
            axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar , get_path ''
    # Path to the directory with the extracted archive:
            axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar , get_path
    # Clean up:
            axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar --- , remove
            axs byquery downloaded,file_name=ILSVRC2012_img_val_500.tar --- , remove

    # Using a generic rule:
            axs byquery extracted,archive_path=$HOME/tmp/ziptest.zip
    """

    logging.warning(f"The resolved extraction_tool_entry '{extraction_tool_entry.get_name()}' located at '{extraction_tool_entry.get_path()}' uses the shell tool '{extraction_tool_entry['tool_path']}'")
    retval = extraction_tool_entry.call('run', [], {"archive_path": archive_path, "target_path": abs_install_dir, "errorize_output": True, "archive_format": archive_format, "strip_components": strip_components})
    if retval == 0:
        return stored_newborn_entry
    else:
        logging.error(f"A problem occured when trying to extract '{archive_path}' into '{abs_install_dir}', bailing out")
        stored_newborn_entry.remove()
        return None
