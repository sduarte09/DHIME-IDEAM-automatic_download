import pandas as pd
import pytest

from dhime.catalog import Station
from dhime.files import DownloadError


class FakeSource:
    """Stands in for the browser: writes a DHIME-like CSV for the requested period."""

    def __init__(self, folder, missing=(), fail=()):
        self.folder, self.missing, self.fail, self.calls = folder, set(missing), set(fail), []

    def download(self, station, start, end):
        self.calls.append((station.code, start, end))
        if station.code in self.missing:
            return None
        if station.code in self.fail:
            raise DownloadError("boom")
        dates = pd.date_range(pd.to_datetime(start, format="%d/%m/%Y"), pd.to_datetime(end, format="%d/%m/%Y"))
        table = pd.DataFrame({"Fecha": dates.strftime("%Y-%m-%d %H:%M:%S"),
                              "Valor": float(station.code[-2:]) + dates.dayofyear / 1000})
        path = self.folder / f"{station.code}-{start.replace('/', '')}-{end.replace('/', '')}.csv"
        table.to_csv(path, index=False)
        return path


@pytest.fixture
def stations():
    return [Station("22050070", "Tolima", 3.4, -75.5, 1679), Station("21140010", "Huila", 3.3, -74.9, 584),
            Station("23050080", "Caldas", 5.3, -75.1, 155)]


@pytest.fixture
def small_bounds():
    return ("01/01/2000", "01/01/2001", "31/12/2001")
