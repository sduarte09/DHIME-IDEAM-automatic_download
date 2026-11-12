"""Download periods. DHIME limits how much can be requested at once, so a long record is split."""
from __future__ import annotations

from typing import NamedTuple

import pandas as pd

DEFAULT_BOUNDARIES = ("01/01/1980", "01/01/1990", "01/01/2000", "01/01/2010", "31/12/2020")


class Chunk(NamedTuple):
    start: str  # dd/mm/yyyy, as typed into the DHIME form
    end: str

    @property
    def key(self):
        return f"{self.start}-{self.end}"


def _parse(text):
    return pd.to_datetime(text, format="%d/%m/%Y")


def date_chunks(boundaries=DEFAULT_BOUNDARIES):
    """Consecutive ``(start, end)`` periods between increasing boundary dates (dd/mm/yyyy).

    Neighbouring chunks share their boundary day, as in the original script.
    """
    parsed = [_parse(b) for b in boundaries]
    if len(parsed) < 2 or any(b <= a for a, b in zip(parsed, parsed[1:])):
        raise ValueError("Boundaries must be at least two dates in increasing order (dd/mm/yyyy)")
    return [Chunk(a, b) for a, b in zip(boundaries[:-1], boundaries[1:])]


def full_range(boundaries=DEFAULT_BOUNDARIES):
    """Daily index from the first to the last boundary."""
    return pd.date_range(_parse(boundaries[0]), _parse(boundaries[-1]), name="Fecha")
