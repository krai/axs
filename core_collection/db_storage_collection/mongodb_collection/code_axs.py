"""
    Usage examples :

                axs byname mongodb_collection , help                                                                                                                        # see this cookbook

        Working with an existing database-based collection:

                axs byname people_collection , all_byquery 'age<99' --template='Name: #{name}# , Age: #{age}#'                                                              # list entries via a report

                axs byname people_collection , byquery name=Leo , own_data                                                                                                  # find one entry

                axs byname people_collection , byquery name=Leo , remove                                                                                                    # remove it

                axs byname people_collection , attached_entry ---own_data='{"_parent_entries":[["^","byname","mongodb_entry"]],"name":"Leo","age":48}' , save               # reinsert it

                axs byname people_collection , byquery name=Leo , plant age 49 , save                                                                                       # modify it

                axs byname people_collection , byquery name=Leo , own_data                                                                                                  # check the result


        Working with a new database-based collection:

                axs work_collection , attached_entry ---own_data='{"_parent_entries":[["^","byname","mongodb_collection"]],"tags":["collection"]}' , save foo_collection    # make a new database-based collection

                axs byname foo_collection , attached_entry ---own_data='{"_parent_entries":[["^","byname","mongodb_entry"]],"name":"John","age":98}' , save                 # store an entry into it

                axs byname foo_collection , all_byquery ''                                                                                                                  # list all entries in it (includes the collection)

                axs byname foo_collection , all_byquery 'age<100'                                                                                                           # list meaningful entries (excludes the collection)

"""


def db_connect(uri, db_name, collection_name):

    from pymongo import MongoClient

    mongo_client            = MongoClient(uri)
    mongo_collection_obj    = mongo_client[db_name][collection_name]

    return mongo_collection_obj


def db_disconnect(mongo_collection_obj):

    mongo_collection_obj.database.client.close()


def generate_contained_entries(mongo_collection_obj, mongodb_parent_entry, __entry__):

    contained_entries = {}

    for document_data in mongo_collection_obj.find():
        print("MongoDB loading document:", document_data)
        document_id     = document_data.pop('_id')

        entry_parents   = document_data.pop('_parent_entries',[])
        entry_parents.append( __entry__.pickle_struct(mongodb_parent_entry) )
        document_data['_parent_entries'] = entry_parents

        found_entry     = __entry__.call("attached_entry", [], { "entry_path": f"mongo_{document_id}", "own_data": document_data } )
        found_entry.call("db_id", [document_id] )

        contained_entries[document_id] = found_entry

    return contained_entries
