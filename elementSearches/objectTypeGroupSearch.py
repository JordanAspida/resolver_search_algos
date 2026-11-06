from .common import cached, store


LABEL = "ObjectTypeGroups"


def search(client):
    if result := cached(client, "object_type_groups"):
        return result
    
    groups = client.object_type_groups.get_all_obj_type_grps()
    used, unused = [], []
    for group in groups:
        obj_types = client.object_type_groups.get_obj_types_for_grp(obj_type_grp_id=group.id)
        if obj_types:
            used.append({**group.model_dump(), "objects": obj_types.name})
        else:
            unused.append(group.model_dump())

    return store(client, "object_type_groups", (used, unused))
