"""The wide output table: one row per day, one column per station code."""
from __future__ import annotations

import pandas as pd

from .periods import DEFAULT_BOUNDARIES, full_range


def new_table(codes, boundaries=DEFAULT_BOUNDARIES):
    return pd.DataFrame(index=full_range(boundaries), columns=list(codes), dtype="float64")


def load_table(path):
    """Read a table written by :func:`save_table` (column names stay strings)."""
    table = pd.read_csv(path, index_col="Fecha", parse_dates=True)
    table.columns = [str(c) for c in table.columns]
    return table


def save_table(table, path):
    table.to_csv(path, index=True, index_label="Fecha")


def ensure_columns(table, codes):
    """Table with empty columns added for codes it does not have yet (existing columns are kept)."""
    new = [c for c in dict.fromkeys(codes) if c not in table.columns]
    if new:
        table = pd.concat([table, pd.DataFrame(float("nan"), index=table.index, columns=new)], axis=1)
    return table


def merge_series(table, code, series):
    """Write ``series`` into column ``code``; days outside the table's range are ignored.

    Returns the number of values written. (The legacy ``all[code][dates] = values`` is a
    chained assignment, which current pandas no longer applies.)
    """
    inside = series[series.index.isin(table.index)]
    table.loc[inside.index, code] = inside.values
    return int(len(inside))


def has_data(table, code, start, end):
    """True if the column has any value between two dd/mm/yyyy dates."""
    if code not in table.columns:
        return False
    a, b = (pd.to_datetime(x, format="%d/%m/%Y") for x in (start, end))
    return bool(table.loc[a:b, code].notna().any())
