from .common import cached, get_user_groups, store


LABEL = "UserGroups"

# Only used if production environment searched

def search(client):
    if result := cached(client, "user_groups"):
        return result
    used, unused = [], []
    for group in get_user_groups(client):
        members = client.user_groups.get_users_in_group(group["id"])
        (used if members else unused).append(group)
    return store(client, "user_groups", (used, unused))
