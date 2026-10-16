from .common import cached, get_data_definitions, store


LABEL = "DataDefinitions"

def search(client):
    # Checking if the results are already cached to avoid redundant API calls
    if result := cached(client, "data_definitions"):
        return result

    used, unused = [], []
    for definition in get_data_definitions(client):
        print(definition.id)
        uses = client.data_definitions.get_data_definition_dependents(data_definition_id=definition.id) # MAKE ACTUAL SDK ENPOINT WITH PYDANTIC SCHEMA

        (used if any(uses.model_dump().values()) else unused).append(
            {**definition.model_dump(), **uses.model_dump()} if any(uses.model_dump().values()) else definition.model_dump()
        )
    return store(client, "data_definitions", (used, unused))
