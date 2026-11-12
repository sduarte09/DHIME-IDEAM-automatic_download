import zipfile

import numpy as np
import pandas as pd
import pytest

from dhime import files, table


def _zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)


def test_wait_for_file_waits_for_the_partial_download_to_finish(tmp_path):
    target = tmp_path / "datos.zip"
    clock = {"t": 0.0}
    steps = []

    def fake_sleep(s):
        clock["t"] += s
        steps.append(clock["t"])
        if len(steps) == 1:
            target.write_bytes(b"x"); (tmp_path / "datos.zip.crdownload").write_bytes(b"")
        if len(steps) == 3:
            (tmp_path / "datos.zip.crdownload").unlink()

    assert files.wait_for_file(target, timeout=10, poll=1, sleep=fake_sleep, clock=lambda: clock["t"]) == target
    assert len(steps) == 3


def test_wait_for_file_times_out(tmp_path):
    clock = {"t": 0.0}
    with pytest.raises(files.DownloadError, match="did not appear"):
        files.wait_for_file(tmp_path / "none.zip", timeout=3, poll=1, sleep=lambda s: clock.update(t=clock["t"] + s),
                            clock=lambda: clock["t"])


def test_extract_download_renames_and_deletes_the_zip(tmp_path):
    z = tmp_path / "datos.zip"
    _zip(z, {"excel.csv.csv": "Fecha,Valor\n2000-01-01,1\n", "../evil.txt": "no"})
    out = files.extract_download(z, tmp_path / "out", "a.csv")
    assert out.read_text() == "Fecha,Valor\n2000-01-01,1\n" and not z.exists()
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["a.csv"] and not (tmp_path / "evil.txt").exists()


def test_extract_download_falls_back_to_a_single_csv_and_rejects_ambiguity(tmp_path):
    z = tmp_path / "d.zip"
    _zip(z, {"other.csv": "Fecha,Valor\n"})
    assert files.extract_download(z, tmp_path, "b.csv", keep_zip=True).exists() and z.exists()
    _zip(z, {"a.csv": "", "b.csv": ""})
    with pytest.raises(files.DownloadError):
        files.extract_download(z, tmp_path, "c.csv")


def test_read_station_csv_sorts_dedups_and_coerces(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("Fecha,Valor\n2000-01-03 00:00:00,3\n2000-01-01 00:00:00,1\n2000-01-02 00:00:00,x\n2000-01-03 00:00:00,4\n")
    s = files.read_station_csv(p)
    assert list(s.index.day) == [1, 2, 3] and s.iloc[0] == 1 and np.isnan(s.iloc[1]) and s.iloc[2] == 4
    (tmp_path / "bad.csv").write_text("a,b\n1,2\n")
    with pytest.raises(files.DownloadError, match="lacks"):
        files.read_station_csv(tmp_path / "bad.csv")


def test_table_merge_ignores_days_outside_the_range():
    t = table.new_table(["1"], ("01/01/2000", "10/01/2000"))
    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["1999-12-31", "2000-01-02", "2000-01-03"]))
    assert table.merge_series(t, "1", s) == 2
    assert t["1"].notna().sum() == 2 and t.loc["2000-01-03", "1"] == 3.0


def test_has_data_and_ensure_columns_and_roundtrip(tmp_path):
    t = table.new_table(["1"], ("01/01/2000", "10/01/2000"))
    t.loc["2000-01-05", "1"] = 1.0
    assert table.has_data(t, "1", "01/01/2000", "06/01/2000") and not table.has_data(t, "1", "06/01/2000", "10/01/2000")
    assert not table.has_data(t, "zzz", "01/01/2000", "10/01/2000")
    t = table.ensure_columns(t, ["1", "22050070"])
    assert list(t.columns) == ["1", "22050070"]
    table.save_table(t, tmp_path / "t.csv")
    back = table.load_table(tmp_path / "t.csv")
    assert list(back.columns) == ["1", "22050070"] and back.index.name == "Fecha" and back.loc["2000-01-05", "1"] == 1.0
