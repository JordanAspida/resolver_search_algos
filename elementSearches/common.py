"""Small read-only helpers for Resolver endpoints not yet wrapped by resolver_sdk."""


from typing import Tuple

def cached(client, key):
    return client.get_derived_cache(key)


def store(client, key, value):
    client.set_derived_cache(key, value)
    return value

