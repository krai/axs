#!/usr/bin/env python3

""" This entry knows how to download a file from a given URL.

    # create a recipe entry:
            axs work_collection , attached_entry examplepage_recipe , plant url http://example.com/  entry_name examplepage_downloaded  file_name example.html  _parent_entries --,:=AS^IS:^:byname:downloader , save

    # activate the recipe, performing the actual downloading:
            axs byname examplepage_recipe , download

    # get the path to the downloaded file:
            axs byname examplepage_downloaded , get_path

    # clean up:
            axs byname examplepage_downloaded , remove
            axs byname examplepage_recipe , remove

"""

import logging


def get_split_file_path(url=None, file_path=None):
    import os

    if file_path:                           # prefer if given
        if type(file_path) == list:
            return file_path
        else:
            return file_path.split(os.sep)
    else:                                   # infer from url otherwise
        return [ os.path.basename(url) ]


def get_uncompressed_split_file_path(split_file_path, uncompress_format):

    if uncompress_format:
        return split_file_path[0:-1] + [ split_file_path[-1].rsplit('.', 1)[0] ]    # trim one .extension off the last syllable
    else:
        return split_file_path


def download(url, abs_result_path, stored_newborn_entry, newborn_entry_path, downloading_tool_entry=None, downloading_tool_cmd_key=None, downloading_tool_params=None, md5=None, md5_tool_entry=None, uncompress_format=None, uncompress_tool_entry=None, abs_patch_path=None, patch_tool_entry=None):
    """Create a new entry and download the url into it

Usage examples:
    # Manual downloading into a new entry:
            axs byname downloader , download 'https://example.com/' example.html --tags,=example

    # Replay of the same command at a later time, stored in a different entry:
            axs byquery downloaded,file_path=example.html , get _replay --entry_name=replay_downloading_example.html

    # Resulting entry path (counter-intuitively) :
            axs byquery downloaded,file_path=example.html , get_path ''

    # Downloaded file path:
            axs byquery downloaded,file_path=example.html , get_path

    # Reaching to the original tool used for downloading:
            axs byquery downloaded,file_path=example.html , get downloading_tool_entry , get tool_path

    # Clean up:
            axs byquery downloaded,file_path=example.html , remove

    # Using a generic rule:
            axs byquery downloaded,url=http://example.com,file_path=example.html

    # Downloading from GoogleDrive (needs a specialized tool):
            axs byname downloader , download --downloading_tool_query+=_from_google_drive --url=https://drive.google.com/uc?id=1XRfiA8wtZEo6SekkJppcnfEr4ghQAS4g --file_path=hello2.text
    """

    if downloading_tool_entry:
        logging.warning(f"The resolved downloading_tool_entry '{downloading_tool_entry.get_name()}' located at '{downloading_tool_entry.get_path()}' uses the shell tool '{downloading_tool_entry['tool_path']}'")

        downloading_tool_param_topup = {"url": url, "target_path": abs_result_path, "record_entry_path": newborn_entry_path, "cmd_key": downloading_tool_cmd_key}
        downloading_tool_params.update( {k:v for k,v in downloading_tool_param_topup.items() if v is not None} )

        retval = downloading_tool_entry.call('run', [], downloading_tool_params)
        if retval != 0:
            logging.error(f"A problem occured when trying to download '{url}' into '{abs_result_path}', bailing out")
            stored_newborn_entry.remove()
            return None
    else:
        logging.error(f"Downloading of {url} requested, but failed to detect a suitable tool")
        stored_newborn_entry.remove()
        return None

    if md5:
        if md5_tool_entry:
            logging.warning(f"The resolved md5_tool_entry '{md5_tool_entry.get_name()}' located at '{md5_tool_entry.get_path()}' uses the shell tool '{md5_tool_entry['tool_path']}'")
            computed_md5 = md5_tool_entry.call('run', [], {"file_path": abs_result_path})
            if computed_md5 != md5:
                logging.error(f"The computed md5 sum '{computed_md5}' is different from the expected '{md5}', bailing out")
                stored_newborn_entry.remove()
                return None
            else:
                logging.warning(f"The computed md5 sum '{computed_md5}' matched the expected one.")
        else:
            logging.error(f"Checking md5 against the value {md5} requested, but failed to detect a suitable tool")
            stored_newborn_entry.remove()
            return None

    if uncompress_format:
        if uncompress_tool_entry:
            logging.warning(f"The resolved uncompress_tool_entry '{uncompress_tool_entry.get_name()}' located at '{uncompress_tool_entry.get_path()}' uses the shell tool '{uncompress_tool_entry['tool_path']}'")
            retval = uncompress_tool_entry.call('run', [], {"target_path": abs_result_path, "in_dir": newborn_entry_path})
            if retval != 0:
                logging.error(f"A problem occured when trying to uncompress {abs_result_path}, bailing out")
                stored_newborn_entry.remove()
                return None
            else:
                logging.error(f"Uncompression from {uncompress_format} successful")
        else:
            logging.error(f"Uncompression from {uncompress_format} requested, but failed to detect a suitable tool")
            stored_newborn_entry.remove()
            return None

    if patch_tool_entry:
        logging.warning(f"The resolved patch_tool_entry '{patch_tool_entry.get_name()}' located at '{patch_tool_entry.get_path()}' uses the shell tool '{patch_tool_entry['tool_path']}'")

        retval = patch_tool_entry.call('run', [], { 'entry_path': abs_result_path, 'abs_patch_path': abs_patch_path} )
        if retval != 0:
            logging.error(f"could not patch \"{abs_result_path}\" with \"{abs_patch_path}\", bailing out")
            stored_newborn_entry.remove()
            return None

    return stored_newborn_entry
