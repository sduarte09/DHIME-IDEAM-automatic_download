from pathlib import Path

import pandas as pd
import pytest

from dhime import catalog, periods

DATA = Path(__file__).parents[1] / "data" / "Datos_Tolima.csv"


def test_parse_code_strips_the_variable_prefix():
    assert catalog.parse_code("pr_22050070") == "22050070"
    assert catalog.parse_code(" 22050070 ") == "22050070"
    for bad in ("pr22050070", "pr_", "abc", ""):
        with pytest.raises(ValueError):
            catalog.parse_code(bad)


@pytest.mark.skipif(not DATA.exists(), reason="example catalogue not present")
def test_reads_the_tolima_example_catalogue():
    stations = catalog.read_catalog(DATA)
    assert len(stations) == 70
    first = stations[0]
    assert (first.code, first.department) == ("23050080", "Caldas")
    assert first.latitude == pytest.approx(5.298916667) and first.longitude == pytest.approx(-75.05747222)
    assert first.elevation == 155


def test_catalogue_errors(tmp_path):
    (tmp_path / "dup.csv").write_text("Codigo;Dpto;Lat;Long;Elevation\npr_1;A;1;1;1\npr_1;B;2;2;2\n")
    with pytest.raises(ValueError, match="Duplicated"):
        catalog.read_catalog(tmp_path / "dup.csv")
    (tmp_path / "nocol.csv").write_text("Code;Dpto\n1;A\n")
    with pytest.raises(ValueError, match="lacks"):
        catalog.read_catalog(tmp_path / "nocol.csv")


def test_default_chunks_cover_four_periods_that_share_their_boundary_day():
    chunks = periods.date_chunks()
    assert len(chunks) == 4
    assert chunks[0] == ("01/01/1980", "01/01/1990") and chunks[1].start == chunks[0].end
    assert chunks[-1].end == "31/12/2020" and chunks[0].key == "01/01/1980-01/01/1990"


def test_invalid_boundaries():
    for bad in (["01/01/2000"], ["01/01/2000", "01/01/2000"], ["01/01/2001", "01/01/2000"]):
        with pytest.raises(ValueError):
            periods.date_chunks(bad)


def test_full_range_matches_the_rows_of_the_example_table():
    idx = periods.full_range()
    assert len(idx) == 14976 and idx[0] == pd.Timestamp("1980-01-01") and idx[-1] == pd.Timestamp("2020-12-31")
