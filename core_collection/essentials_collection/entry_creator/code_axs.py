import os

def parent_list_from_names(newborn_parent_names, protected=True):

    protected_parent_list = [ "AS^IS" ] if protected else []

    for parent_name in newborn_parent_names:
        protected_parent_list.append( [ "^", "byname", parent_name ] )

    return protected_parent_list


def path_to_list(path_or_list):
    """
        A generic ufun.py candidate?
    """

    if not path_or_list:
        return []
    elif type(path_or_list)==list:
        return path_or_list
    else:
        return os.path.split(path_or_list)


def get_result_path(relative_to_dir, inside_install_dir):

    if relative_to_dir or inside_install_dir:
        return os.path.join( *(path_to_list(relative_to_dir)), *(path_to_list(inside_install_dir)) )
    else:
        return None


def make_abs_install_dir_if_necessary(newborn_entry_path, rel_install_dir):
    """
        The assumption here is that "rel_install_dir" contains the path that we want to be auto-created for us,
        whereas "inside_install_dir" is the path that the user code will create as a side-effect of extraction.
        Either can independently be a path list, a path string or empty.
    """

    if rel_install_dir:
        abs_install_dir = os.path.join(newborn_entry_path, *(path_to_list(rel_install_dir)) )
        os.makedirs( abs_install_dir )
    else:
        abs_install_dir = newborn_entry_path

    return abs_install_dir
