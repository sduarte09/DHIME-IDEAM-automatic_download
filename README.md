![tests](https://github.com/sduarte09/DHIME-IDEAM-automatic_download/actions/workflows/tests.yml/badge.svg)

# DHIME-IDEAM automatic download

Downloads daily station data from the **DHIME** portal of IDEAM, the Colombian institute of hydrology, meteorology and environmental studies (<http://dhime.ideam.gov.co/atencionciudadano/>), and collects it in one CSV table: one row per day, one column per station code. The portal serves one station and a limited period per request, so this tool drives Chrome through the web form, request by request, and can resume where it stopped.

The default settings download daily precipitation (`PRECIPITACION` / `PTPM_CON`) from 1980 to 2020 in four periods. `data/Datos_Tolima.csv` lists 70 stations of Tolima and neighbouring departments as an example.

## Status

| Part | Status |
|---|---|
| Station catalogue, periods, file handling, output table, resume (`dhime.catalog`, `periods`, `files`, `table`, `state`, `downloader`) | tested with a fake browser |
| Command line (`dhime-download`, including `--dry-run`) | tested |
| Chrome driver (`dhime.browser`) | **not run against the live portal** |

**What has not been verified.** The Chrome driver is a port of the 2022 script to the Selenium 4 API. It was written and its page locators were checked for formatting, but it has not been run against the current DHIME site: this was developed without a browser or internet access. If the portal has changed, update the `LOCATORS` table at the top of `src/dhime/browser.py`; the rest of the code does not depend on the page. Please run it on one station first (`--limit 1`). Tests run on Python 3.12 locally and on 3.10 and 3.12 in GitHub Actions.

## Installation

You need Google Chrome and Python 3.10 or newer.

```bash
git clone https://github.com/sduarte09/DHIME-IDEAM-automatic_download.git
cd DHIME-IDEAM-automatic_download
pip install -e ".[browser,test]"
```

Selenium 4.6+ downloads the matching Chrome driver itself; `webdriver_manager` is no longer needed.

## Usage

Check what would be requested, without opening a browser:

```bash
dhime-download --catalog data/Datos_Tolima.csv --output Tolima.csv --dry-run
```

Download (try one station first):

```bash
dhime-download --catalog data/Datos_Tolima.csv --output Tolima.csv --limit 1
dhime-download --catalog data/Datos_Tolima.csv --output Tolima.csv
```

Useful options: `--headless`, `--wait 30` (slow connection), `--boundaries 01/01/1990 31/12/2020` (other periods), `--parameter` and `--variable` (other DHIME variables), `--retry-missing`, `--keep-files`.

**Resuming.** Stop the run at any time and start it again: a station and period is skipped when the output table already has values for it or `dhime_progress.json` marks it done. The table is saved after every station. Stations that the portal does not offer are remembered and skipped on later runs unless you pass `--retry-missing`.

From Python:

```python
from dhime import read_catalog, download_stations
from dhime.browser import DhimeBrowser

stations = read_catalog("data/Datos_Tolima.csv")
with DhimeBrowser("downloads", headless=True) as browser:
    report = download_stations(stations, browser, "Tolima.csv", state_path="dhime_progress.json")
print(report.missing, report.failed)
```

### Input and output

- **Catalogue:** CSV with `;` separator and columns `Codigo;Dpto;Lat;Long;Elevation`. Codes may carry a prefix (`pr_22050070`); the table uses the digits only (`22050070`). `Dpto` must match the department name in the portal.
- **Output:** `Tolima.csv`, with a `Fecha` column and one column per station. Days without data are empty. An existing file is extended, and columns for stations that are not in the catalogue are kept.

## Repository layout

```
src/dhime/    Python 3 package
tests/        pytest tests (fake browser, no internet needed)
data/         Datos_Tolima.csv (example catalogue)
legacy/       the original script, unchanged
docs/         notes on the legacy code; workshop slides
```

## Tests

```bash
pytest
```

## Responsible use and data

The data belong to IDEAM. Check the terms of use of the DHIME portal before redistributing downloaded data, and cite IDEAM as the source. The tool makes the requests a person would make through the web form, one at a time, with waits between them; please do not run several copies in parallel.

## Acknowledgements

The browser automation originates from a script by John Alexander Sandoval Barrera (Universidad Nacional de Colombia, 2021), edited by Santiago Duarte (IHE Delft, 2022). The slides `docs/Automate large data extraction.pptx` are from a workshop given in October 2022.

## License

MIT, see `LICENSE`.
