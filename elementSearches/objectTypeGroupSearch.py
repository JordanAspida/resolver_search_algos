from .common import cached, data, store


LABEL = "ObjectTypeGroups"


def search(client):
    if result := cached(client, "object_type_groups"):
        return result
    groups = data(client.safe_get("/object/objectTypeGroup"))
    used, unused = [], []
    for group in groups:
        members = data(client.safe_get(f"/object/objectTypeGroup/{group['id']}/objectType"))
        if members:
            used.append({**group, "objects": members})
        else:
            unused.append(group)
    return store(client, "object_type_groups", (used, unused))
