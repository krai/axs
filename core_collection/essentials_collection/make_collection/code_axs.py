"""
    Usage examples :

                axs byname make_collection , help                                                                       # see this cookbook

                axs byquery collection,collection_name=vehicle_collection --parent_recursion+                           # make a new collection (or rather make sure it is there)

                axs byname vehicle_collection , attached_entry ---own_data='{"make":"Tesla","model":"X","doors":"gullwing"}' , save tesla_x     # adding an entry to the collection

                axs byname tesla_x , get_path                                                                           # should show the path within vehicle_collection

                axs byname vehicle_collection , remove                                                                  # collections are removed as any other entries


        A collection may be set up auto-indexing, i.e. not updating the index every time a contained entry is added or removed - good for concurrent execution of multiple axs's

                axs byquery collection,collection_name=vehicle_collection,contained_entries=auto --parent_recursion+    # auto-indexing new collection


        Adding a collection into another collection: containing_collection_name is a "second class" parameter not expected to end up in the created entry

                axs byquery collection,collection_name=ev_collection --,::=containing_collection_name:vehicle_collection --parent_recursion+    # make ev_collection inside vehicle_collection
"""

