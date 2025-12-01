def as_bool(value):
    """
    Returns true if the raw value given is truthy, false otherwise.
    """
    return str(value).lower() in ("yes", "true", "1")


def as_csv_list(value):
    return str(value).split(",")