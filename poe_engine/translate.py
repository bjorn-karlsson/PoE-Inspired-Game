"""Turn rolled modifier stats into human-readable lines.

This mirrors (a small slice of) Path of Exile's stat-description system: a
modifier carries one or more ``stats`` (each with an id and a rolled value) and
the translation data tells us how to render them, e.g.::

    {"id": "physical_damage_+%", "value": 25} -> "25% increased Physical Damage"
"""

from . import data


def _apply_handlers(value, handlers):
    for handler in handlers or ():
        if handler in ("divide_by_one_hundred", "divide_by_one_hundred_2dp",
                       "divide_by_one_hundred_2dp_if_required"):
            value = value / 100
        elif handler == "negate":
            value = -value
        elif handler == "milliseconds_to_seconds":
            value = value / 1000
    return value


def _format_value(value, fmt):
    if fmt == "ignore":
        return None
    rendered = int(value) if float(value).is_integer() else round(value, 2)
    if fmt == "+#":
        return f"+{rendered}"
    return str(rendered)


def translate_stats(stats: list) -> list:
    """Translate a list of ``{"id", "value"}`` dicts into readable strings.

    Falls back to a raw ``id value`` representation when no translation exists,
    so callers always get *something* to show.
    """
    index = data.translation_index()
    remaining = list(stats)
    lines = []

    while remaining:
        # Greedily try to match the largest group of remaining ids first so that
        # combined lines ("Adds # to # Damage") render correctly.
        ids_present = [s["id"] for s in remaining]
        entry = None
        matched = []
        for size in range(len(ids_present), 0, -1):
            key = frozenset(ids_present[:size])
            entry = index.get(key)
            if entry is not None:
                matched = remaining[:size]
                break

        if entry is None:
            stat = remaining.pop(0)
            lines.append(f"{stat['id']} {stat.get('value', '')}".strip())
            continue

        line = _render(entry, matched)
        if line:
            lines.append(line)
        remaining = remaining[len(matched):]

    return lines


def _render(entry, stats):
    template = entry["string"]
    formats = entry.get("format", [])
    handlers = entry.get("index_handlers", [])

    rendered = template
    for i, stat in enumerate(stats):
        value = stat.get("value", stat.get("min", 0))
        value = _apply_handlers(value, handlers[i] if i < len(handlers) else None)
        fmt = formats[i] if i < len(formats) else "#"
        shown = _format_value(value, fmt)
        if shown is None:
            shown = ""
        rendered = rendered.replace(f"{{{i}}}", shown)

    return " ".join(rendered.split())
