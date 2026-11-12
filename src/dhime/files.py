"""Handling of the files DHIME produces: the downloaded zip and the station CSV inside it."""
from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path

import pandas as pd

ZIP_NAME = "datos.zip"
MEMBER = "excel.csv.csv"  # name of the CSV inside the zip, as DHIME writes it


class DownloadError(RuntimeError):
    """A download did not produce the expected file."""


def wait_for_file(path, timeout=60.0, poll=0.5, sleep=time.sleep, clock=time.monotonic):
    """Wait until ``path`` exists and Chrome has finished writing it (no ``.crdownload`` next to it)."""
    path = Path(path)
    deadline = clock() + timeout
    while clock() < deadline:
        if path.exists() and not Path(str(path) + ".crdownload").exists():
            return path
        sleep(poll)
    raise DownloadError(f"{path.name} did not appear within {timeout:g} s")


def extract_download(zip_path, dest_dir, new_name, member=MEMBER, keep_zip=False):
    """Extract the station CSV from the downloaded zip as ``dest_dir/new_name`` and delete the zip.

    Only the one expected member is extracted (never ``extractall``). If DHIME changes the
    member name and the zip holds a single ``.csv`` file, that file is used.
    """
    zip_path, dest_dir = Path(zip_path), Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / new_name
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if member not in names:
            csvs = [n for n in names if n.lower().endswith(".csv")]
            if len(csvs) != 1:
                raise DownloadError(f"{zip_path.name} holds {names}; expected {member!r}")
            member = csvs[0]
        with zf.open(member) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)
    if not keep_zip:
        zip_path.unlink()
    return target


def read_station_csv(path):
    """Daily series (``Fecha`` -> ``Valor``) of a downloaded station file, sorted, one value per day."""
    table = pd.read_csv(path)
    missing = {"Fecha", "Valor"} - set(table.columns)
    if missing:
        raise DownloadError(f"{Path(path).name} lacks column(s) {sorted(missing)}; found {list(table.columns)}")
    series = pd.Series(pd.to_numeric(table["Valor"], errors="coerce").values,
                       index=pd.to_datetime(table["Fecha"]).dt.normalize(), name="Valor")
    return series[~series.index.duplicated(keep="last")].sort_index()
