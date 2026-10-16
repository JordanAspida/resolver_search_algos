"""Small read-only helpers for Resolver endpoints not yet wrapped by resolver_sdk."""


from typing import Tuple


def data(response):
    """Return the list payload from either a list or Resolver response envelope."""
    return response.get("data", []) if isinstance(response, dict) else response


def cached(client, key):
    return client.get_derived_cache(key)


def store(client, key, value):
    client.set_derived_cache(key, value)
    return value


def get_object_types(client):
    return data(client.safe_get("/object/objectType")) # MAKE ACTUAL SDK ENPOINT


def get_fields(client):
    return client.fields.get_all_fields()


def get_data_definitions(client):
    return client.data_definitions.get_all_data_definitions()


def get_user_groups(client):
    return data(client.safe_get("/user/group")) # MAKE ACTUAL SDK ENPOINT


def get_formula_by_object_type(client, object_type_id):
    return data(client.safe_get(f"/object/objectType/{object_type_id}/formula")) # MAKE ACTUAL SDK ENPOINT
