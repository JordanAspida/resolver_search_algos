from .common import cached, store


LABEL = "ObjectTypes"

# This search is calssified by whether any object exists for a specific object type in the target environment 
# Might not be the most useful search as object types might be used only in certain envs etc.
# Only ever run this search on a live env as in a sandbox environment it is pointless
def search(client):
    if result := cached(client, "object_types"):
        return result
    
    used, unused = [], []
    for object_type in client.object_types.get_all_obj_types():
        count = client.objects.object_count(object_type.id)
        print(f"Object type: {object_type.name} ({object_type.id}), count: {count}")
        (used if count > 0 else unused).append(object_type.model_dump())

    return store(client, "object_types", (used, unused))
