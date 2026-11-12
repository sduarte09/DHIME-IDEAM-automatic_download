"""Download many stations over several periods into one wide table, with resume."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from .files import DownloadError, read_station_csv
from .periods import DEFAULT_BOUNDARIES, date_chunks
from .state import DownloadState
from .table import ensure_columns, has_data, load_table, merge_series, new_table, save_table


class Source(Protocol):
    """Anything that can fetch one station and period (the browser, or a fake in tests)."""

    def download(self, station, start: str, end: str) -> Optional[Path]:
        """Path of a CSV with ``Fecha`` and ``Valor`` columns, or ``None`` if the station is not offered."""


@dataclass
class Report:
    downloaded: list = field(default_factory=list)  # (code, chunk key, n values)
    skipped: list = field(default_factory=list)     # (code, chunk key): already there
    missing: list = field(default_factory=list)     # codes the portal does not offer
    failed: list = field(default_factory=list)      # (code, chunk key, message)


def download_stations(stations, source, output_csv, boundaries=DEFAULT_BOUNDARIES, state_path=None,
                      retry_missing=False, limit=None, keep_files=False, log=print):
    """Download every station and period, saving the table after each station.

    Parameters
    ----------
    stations : list of :class:`dhime.catalog.Station`
    source : object with ``download(station, start, end)`` (see :class:`Source`)
    output_csv : the wide table; an existing file is extended, not overwritten
    state_path : optional progress file (``None`` = rely on the data in the table only)
    retry_missing : try again the stations the portal did not offer on an earlier run
    limit : stop after this many stations (those skipped as complete do not count)
    keep_files : keep the per-station CSV files that the source returns

    A period is skipped when the progress file marks it done or the table already has values
    for that station and period. A :class:`dhime.files.DownloadError` for one period is
    recorded in the report and the run goes on with the next station.
    """
    output_csv = Path(output_csv)
    chunks = date_chunks(boundaries)
    table = load_table(output_csv) if output_csv.exists() else new_table([], boundaries)
    table = ensure_columns(table, [s.code for s in stations])
    state = DownloadState(state_path)
    report, attempted = Report(), 0
    try:
        for station in stations:
            if station.code in state.missing and not retry_missing:
                report.missing.append(station.code)
                continue
            pending = [c for c in chunks if not (state.is_done(station.code, c) or has_data(table, station.code, *c))]
            report.skipped += [(station.code, c.key) for c in chunks if c not in pending]
            if not pending:
                continue
            if limit is not None and attempted >= limit:
                break
            attempted += 1
            log(f"Station {station.code} ({station.department}): {len(pending)} period(s)")
            for chunk in pending:
                try:
                    path = source.download(station, chunk.start, chunk.end)
                    if path is None:
                        state.mark_missing(station.code)
                        report.missing.append(station.code)
                        log(f"    {station.code} not found")
                        break
                    series = read_station_csv(path)
                except DownloadError as err:
                    report.failed.append((station.code, chunk.key, str(err)))
                    log(f"    {station.code} {chunk.key} failed: {err}")
                    break
                n = merge_series(table, station.code, series)
                state.mark_done(station.code, chunk)
                report.downloaded.append((station.code, chunk.key, n))
                if not keep_files:
                    Path(path).unlink(missing_ok=True)
            save_table(table, output_csv)
            state.save()
    finally:
        save_table(table, output_csv)
        state.save()
    return report
