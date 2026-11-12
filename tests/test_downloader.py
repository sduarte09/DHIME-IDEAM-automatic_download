import numpy as np
import pandas as pd

from conftest import FakeSource
from dhime import downloader, state, table


def run(stations, tmp_path, bounds, source=None, **kw):
    src = source or FakeSource(tmp_path)
    out = tmp_path / "table.csv"
    rep = downloader.download_stations(stations, src, out, bounds, state_path=tmp_path / "p.json", log=lambda *_: None, **kw)
    return rep, src, out


def test_full_run_fills_the_table(stations, small_bounds, tmp_path):
    rep, src, out = run(stations, tmp_path, small_bounds)
    t = table.load_table(out)
    assert list(t.columns) == ["22050070", "21140010", "23050080"] and len(rep.downloaded) == 6
    assert t.index[0] == pd.Timestamp("2000-01-01") and t.index[-1] == pd.Timestamp("2001-12-31")
    assert t.notna().all().all()
    assert t.loc["2000-03-01", "22050070"] == 70 + 61 / 1000  # value written for the right day
    assert not list(tmp_path.glob("2205*.csv"))  # per-station files are removed


def test_second_run_downloads_nothing(stations, small_bounds, tmp_path):
    run(stations, tmp_path, small_bounds)
    rep, src, _ = run(stations, tmp_path, small_bounds)
    assert src.calls == [] and rep.downloaded == [] and len(rep.skipped) == 6


def test_resume_from_the_table_alone_without_a_progress_file(stations, small_bounds, tmp_path):
    run(stations, tmp_path, small_bounds)
    (tmp_path / "p.json").unlink()
    rep, src, _ = run(stations, tmp_path, small_bounds)
    assert src.calls == []


def test_partial_table_only_requests_the_missing_period(stations, small_bounds, tmp_path):
    t = table.new_table([s.code for s in stations], small_bounds)
    t.loc["2000-06-01", "22050070"] = 5.0  # first period already has data
    table.save_table(t, tmp_path / "table.csv")
    rep, src, _ = run(stations, tmp_path, small_bounds)
    assert ("22050070", "01/01/2000", "01/01/2001") not in src.calls
    assert ("22050070", "01/01/2001", "31/12/2001") in src.calls


def test_missing_station_is_remembered_and_retried_on_request(stations, small_bounds, tmp_path):
    rep, src, _ = run(stations, tmp_path, small_bounds, FakeSource(tmp_path, missing={"21140010"}))
    assert rep.missing == ["21140010"] and sum(c[0] == "21140010" for c in src.calls) == 1  # stopped after first period
    assert "21140010" in state.DownloadState(tmp_path / "p.json").missing
    rep2, src2, _ = run(stations, tmp_path, small_bounds)
    assert rep2.missing == ["21140010"] and not any(c[0] == "21140010" for c in src2.calls)
    rep3, src3, _ = run(stations, tmp_path, small_bounds, retry_missing=True)
    assert sum(c[0] == "21140010" for c in src3.calls) == 2


def test_a_failed_download_is_reported_and_the_run_continues(stations, small_bounds, tmp_path):
    rep, src, out = run(stations, tmp_path, small_bounds, FakeSource(tmp_path, fail={"21140010"}))
    assert [f[0] for f in rep.failed] == ["21140010"] and rep.failed[0][2] == "boom"
    t = table.load_table(out)
    assert t["23050080"].notna().all() and t["21140010"].isna().all()
    rep2, src2, _ = run(stations, tmp_path, small_bounds)  # failure is not remembered: it is retried
    assert sum(c[0] == "21140010" for c in src2.calls) == 2


def test_limit_counts_only_stations_that_need_work(stations, small_bounds, tmp_path):
    rep, src, _ = run(stations, tmp_path, small_bounds, limit=2)
    assert {c[0] for c in src.calls} == {"22050070", "21140010"}
    rep2, src2, _ = run(stations, tmp_path, small_bounds, limit=2)
    assert {c[0] for c in src2.calls} == {"23050080"}


def test_existing_columns_of_other_stations_are_kept(stations, small_bounds, tmp_path):
    t = table.new_table(["99999999"], small_bounds)
    t["99999999"] = 1.0
    table.save_table(t, tmp_path / "table.csv")
    run(stations, tmp_path, small_bounds)
    back = table.load_table(tmp_path / "table.csv")
    assert "99999999" in back.columns and back["99999999"].eq(1.0).all()


def test_interrupted_run_keeps_what_was_downloaded(stations, small_bounds, tmp_path):
    class Boom(FakeSource):
        def download(self, station, start, end):
            if station.code == "23050080":
                raise KeyboardInterrupt
            return super().download(station, start, end)

    try:
        run(stations, tmp_path, small_bounds, Boom(tmp_path))
    except KeyboardInterrupt:
        pass
    back = table.load_table(tmp_path / "table.csv")
    assert back["22050070"].notna().all() and back["23050080"].isna().all()
