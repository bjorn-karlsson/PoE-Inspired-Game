"""JSON serialization helpers.

Any object that exposes ``reprJSON()`` can be turned into JSON.  This keeps the
domain classes free of serialization details while still giving us readable
debug output.
"""

import json


class ComplexEncoder(json.JSONEncoder):
    """JSON encoder that defers to an object's ``reprJSON`` method."""

    def default(self, obj):
        repr_json = getattr(obj, "reprJSON", None)
        if callable(repr_json):
            return repr_json()
        return super().default(obj)


def to_json(obj, indent=4):
    """Serialize *obj* to a JSON string using :class:`ComplexEncoder`."""
    return json.dumps(obj, cls=ComplexEncoder, indent=indent)


def print_json(obj, indent=4):
    """Pretty-print *obj* as JSON to stdout."""
    print(to_json(obj, indent=indent))
