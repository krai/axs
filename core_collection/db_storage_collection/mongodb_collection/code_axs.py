"""
    Usage examples :
                axs byname mongodb_collection , all_byquery 'age<99' --template='Name: #{name}# , Age: #{age}#'

                axs byname mongodb_collection , byquery name=Leo , own_data

                axs byname mongodb_collection , byquery name=Leo , remove

                axs byname mongodb_collection , attached_entry ---own_data='{"_parent_entries":[["^","byname","mongodb_entry"]],"name":"Leo","age":48}' , save

                axs byname mongodb_collection , byquery name=Leo , plant age 49 , save

                axs byname mongodb_collection , byquery name=Leo , own_data
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
