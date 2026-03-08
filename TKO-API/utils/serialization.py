from datetime import datetime


def row_with_iso_dates(row):
    """Convert datetime fields to ISO strings for JSON responses."""
    if not row:
        return row

    converted = dict(row)

    for key, value in converted.items():
        if isinstance(value, datetime):
            converted[key] = value.isoformat()

    return converted


def rows_with_iso_dates(rows):
    return [row_with_iso_dates(row) for row in rows]
