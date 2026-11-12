"""Station catalogue (the ``Datos_*.csv`` files)."""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

_CODE = re.compile(r"^(?:[A-Za-z]+_)?(\d+)$")


@dataclass(frozen=True)
class Station:
    code: str  # IDEAM station code, digits only (``pr_22050070`` -> ``22050070``)
    department: str
    latitude: float
    longitude: float
    elevation: float


def parse_code(value):
    """Station code without its variable prefix; ``ValueError`` if it is not ``[prefix_]digits``."""
    match = _CODE.match(str(value).strip())
    if not match:
        raise ValueError(f"Cannot read station code {value!r}; expected digits with an optional prefix like 'pr_'")
    return match.group(1)


def read_catalog(path, sep=";"):
    """Read a catalogue with columns ``Codigo``, ``Dpto``, ``Lat``, ``Long`` and ``Elevation``.

    Returns a list of :class:`Station`. Duplicated codes raise ``ValueError``.
    """
    table = pd.read_csv(path, sep=sep, dtype={"Codigo": str})
    missing = {"Codigo", "Dpto"} - set(table.columns)
    if missing:
        raise ValueError(f"Catalogue {path} lacks column(s) {sorted(missing)}")
    num = lambda name: pd.to_numeric(table[name], errors="coerce") if name in table else pd.Series(float("nan"), index=table.index)
    lat, lon, elev = num("Lat"), num("Long"), num("Elevation")
    stations = [Station(parse_code(c), str(d).strip(), float(a), float(o), float(e))
                for c, d, a, o, e in zip(table["Codigo"], table["Dpto"], lat, lon, elev)]
    codes = [s.code for s in stations]
    dup = sorted({c for c in codes if codes.count(c) > 1})
    if dup:
        raise ValueError(f"Duplicated station codes in {path}: {dup}")
    return stations
