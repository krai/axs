
def db_id(db_id=None, __entry__=None):
    """ Getter/Setter for MongoDB id (an object of ObjectId class)
    """
    if db_id:
        __entry__.stored_db_id = db_id

    return __entry__.stored_db_id if hasattr(__entry__, "stored_db_id") else None


def save(__entry__):

    mongodb_collection      = __entry__.get_container()
    mongo_collection_obj    = mongodb_collection.get("mongo_collection_obj")
    mongodb_parent_entry    = mongodb_collection.get("mongodb_parent_entry")

    db_id           = __entry__.call("db_id")

    sanitized_data  = __entry__.pickle_struct(__entry__.own_data())
    allowed_parents = __entry__.pickle_struct( [ p for p in __entry__.parents_loaded() if p!=mongodb_parent_entry ] )

    if allowed_parents==[]:
        sanitized_data.pop('_parent_entries', None)
    else:
        sanitized_data['_parent_entries'] = allowed_parents

    if db_id:
        result = mongo_collection_obj.replace_one({"_id": db_id}, sanitized_data)

        if result.matched_count==1 and result.modified_count==1:
            print(f"Successfully updated {db_id} in the database")
        else:
            print("Failed to update {db_id} in the database")
    else:
        result  = mongo_collection_obj.insert_one(sanitized_data)
        db_id   = result.inserted_id

        if db_id:
            print(f"Successfully inserted {db_id} into the database")
            __entry__.call("db_id", db_id)
        else:
            print("Failed to insert the entry {sanitized_data} into the database")

    return __entry__


def remove(__entry__):

    mongo_collection_obj    = __entry__.get_container().get("mongo_collection_obj")

    db_id                   = __entry__.call("db_id")
    result                  = mongo_collection_obj.delete_one({"_id": db_id})

    if result.deleted_count==1:
        print(f"Successfully deleted {db_id} from the database")
        __entry__.call("db_id", None)
    else:
        print("Failed to delete {db_id} from the database")

    return __entry__
