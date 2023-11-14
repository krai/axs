
def parent_list_from_names(newborn_parent_names, protected=True):

    protected_parent_list = [ "AS^IS" ] if protected else []

    for parent_name in newborn_parent_names:
        protected_parent_list.append( [ "^", "byname", parent_name ] )

    return protected_parent_list
