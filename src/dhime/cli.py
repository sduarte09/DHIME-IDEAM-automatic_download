"""Command line: ``dhime-download --catalog data/Datos_Tolima.csv --output Tolima.csv``."""
from __future__ import annotations

import argparse
import sys

from .catalog import read_catalog
from .downloader import download_stations
from .periods import DEFAULT_BOUNDARIES, date_chunks


def build_parser():
    p = argparse.ArgumentParser(prog="dhime-download", description="Download IDEAM DHIME station data into one CSV table.")
    p.add_argument("--catalog", required=True, help="station catalogue (CSV with ; separator: Codigo;Dpto;Lat;Long;Elevation)")
    p.add_argument("--output", required=True, help="wide CSV table to create or extend")
    p.add_argument("--download-dir", default="downloads", help="folder for Chrome's temporary downloads")
    p.add_argument("--progress", default="dhime_progress.json", help="progress file for resuming ('' to disable)")
    p.add_argument("--parameter", default="PRECIPITACION")
    p.add_argument("--variable", default="PTPM_CON")
    p.add_argument("--boundaries", nargs="+", default=list(DEFAULT_BOUNDARIES), metavar="DD/MM/YYYY",
                   help="period boundaries; consecutive pairs are requested one by one")
    p.add_argument("--wait", type=float, default=15, help="seconds to wait for page elements")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--limit", type=int, help="stop after this many stations")
    p.add_argument("--retry-missing", action="store_true", help="try again stations the portal did not offer")
    p.add_argument("--keep-files", action="store_true", help="keep the per-station CSV files")
    p.add_argument("--dry-run", action="store_true", help="show what would be requested; open no browser")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    stations = read_catalog(args.catalog)
    chunks = date_chunks(args.boundaries)
    if args.dry_run:
        print(f"{len(stations)} stations x {len(chunks)} periods = {len(stations) * len(chunks)} requests")
        for c in chunks:
            print(f"  {c.start} -> {c.end}")
        return 0
    from .browser import DhimeBrowser

    with DhimeBrowser(args.download_dir, args.parameter, args.variable, args.wait, args.headless) as browser:
        report = download_stations(stations, browser, args.output, args.boundaries, args.progress or None,
                                   args.retry_missing, args.limit, args.keep_files)
    print(f"downloaded {len(report.downloaded)} period(s); missing {len(set(report.missing))} station(s); "
          f"failed {len(report.failed)}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
