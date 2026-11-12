"""Automatic download of IDEAM (Colombia) station data from the DHIME portal."""
from .catalog import Station, read_catalog
from .downloader import Report, download_stations
from .files import DownloadError
from .periods import DEFAULT_BOUNDARIES, Chunk, date_chunks

__version__ = "0.1.0"
__all__ = ["Station", "read_catalog", "Report", "download_stations", "DownloadError", "DEFAULT_BOUNDARIES",
           "Chunk", "date_chunks"]
