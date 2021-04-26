

def download(url, entry_name, file_name, __entry__):
    """Create a new entry and download the url into it

Usage examples:
    Manual downloading into a new entry:
            axs byname downloader , download 'https://example.com' examplepage_downloaded example.html
    Resulting entry path (counter-intuitively) :
            axs byname examplepage_downloaded , get_path ''
    Downloaded file path:
            axs byname examplepage_downloaded , get_path
    Reaching to the original producer (this Entry):
            axs byname examplepage_downloaded , get producer , get_path
    Clean up:
            rm -rf "`axs byname examplepage_downloaded , get_path ''`"
            axs work_collection , remove_entry_name examplepage_downloaded
    """
    data = {
        'url':          url,
        'file_name':    file_name,
        'remark':       'downloaded via URL',
        'producer^':    '^byname:downloader'
    }

    work_collection = __entry__.get_kernel().work_collection()
    target_path     = work_collection.bypath(entry_name).call('save', [], data).get_path(file_name)

    work_collection.call('add_entry_path', entry_name )

    if __entry__.call('download_to_path', [url, target_path]) == 0:   # does not have to be the new entry, but needs to inherit from shell
        return target_path
    else:
        return None


def download_to_path(url, target_path, __entry__):
    """Pick a specific method and download a url into target_path

Usage examples :
            axs byname downloader , download_to_path http://example.com exmpl.html
    """
    print('url = "{}", target_path = "{}"'.format(url, target_path))
    return __entry__.call('wget', [url, target_path])


def wget(url, target_path, __entry__):
    """Download a url into a file using wget

Usage examples :
            axs byname downloader , wget http://example.com exmpl.html
    """
    shell_cmd = 'wget -O {} {}'.format(target_path, url)
    return __entry__.call('run', [shell_cmd])



def curl(url, target_path, __entry__):
    """Download a url into a file using curl

Usage examples :
            axs byname downloader , curl http://example.com exmpl.html
    """
    shell_cmd = 'curl -o {} {}'.format(target_path, url)
    return __entry__.call('run', [shell_cmd])
