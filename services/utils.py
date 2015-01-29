import uuid


def matching_uuids(first, second, version=4):
    try:
        if not isinstance(first, uuid.UUID):
            first = uuid.UUID(first, version=version)
        if not isinstance(second, uuid.UUID):
            second = uuid.UUID(second, version=version)
    except ValueError:
        return False
    return first == second
