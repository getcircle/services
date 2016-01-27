

def get_path_from_dict(path, source):
    """Return the given path from the dictionary

    Args:
        path (str): path to fetch from the dictionary (can be a dotted path)
        source (dict): dictionary to fetch values from

    Returns:
        any: value within dict at path

    Raises:
        KeyError: raises a key error if any part of the path is not found in the dict.

    """
    remainder = None
    if '.' in path:
        path, remainder = path.split('.', 1)

    value = source[path]
    if isinstance(value, dict) and remainder:
        return get_path_from_dict(remainder, value)
    else:
        return value


def set_path_in_dict(path, value, source):
    """Set a value within the dict based on the path.

    Args:
        path (str): path to set within the source dictionary
        value (any): value to set at path
        source (dict): dict to set the value within

    """
    remainder = None
    if '.' in path:
        path, remainder = path.split('.', 1)

    path_value = source.get(path, {})
    if remainder:
        return set_path_in_dict(remainder, value, path_value)
    else:
        source[path] = value
