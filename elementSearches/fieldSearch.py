from .common import cached, store
import logging
logger = logging.getLogger(__name__)


LABEL = "Fields"


def search(client):
    if result := cached(client, "fields"):
        return result
    
    used, unused = [], []
    for field in client.fields.get_all_fields(client):
        logger.info(f"Searching use of field: {field.name} ({field.id}) ...")
        object_types = {obj_type.id: obj_type for obj_type in client.fields.get_all_obj_types_for_field(field.id)}
        if object_types:
            used.append({**field.model_dump(), "objectTypes": object_types})
        else:
            unused.append({**field.model_dump()})

    return store(client, "fields", (used, unused))
