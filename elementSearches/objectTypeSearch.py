from .common import cached, get_object_types, store


LABEL = "ObjectTypes"


def search(client):
    """Classify object types by whether they contain at least one object."""
    if result := cached(client, "object_types"):
        return result
    used, unused = [], []
    for object_type in get_object_types(client):
        count = client.objects.object_count(object_type["id"])
        print(f"Object type: {object_type['name']} ({object_type['id']}), count: {count}")
        (used if count > 0 else unused).append(object_type)
    return store(client, "object_types", (used, unused))
