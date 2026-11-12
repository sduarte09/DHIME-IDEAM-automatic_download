# Notes on the legacy script

`legacy/Download IDEAM.py` (Sandoval Barrera 2021, edited by Duarte 2022) is unchanged. This
file lists what was found in it and what `src/dhime` does instead. The package was tested with a
fake browser; the Selenium driver was **not** run against the live portal.

## Things that no longer run on current libraries

- Selenium 3 API: `find_element_by_css_selector`, `find_element_by_id`, `find_element_by_xpath`
  and `webdriver.Chrome(path, options=...)` were removed in Selenium 4. `dhime.browser` uses
  `find_element(By..., ...)` and Selenium Manager, so `webdriver_manager` is not needed.
- `all[Code][dates] = values` is a chained assignment, which pandas no longer applies reliably
  (and not at all with copy-on-write in pandas 3). `dhime.table.merge_series` uses `.loc`.

## Likely bugs

- **Column names.** A new table is created with the catalogue codes including the prefix
  (`pr_22050070`), but values are written with the prefix removed (`22050070`), which raises
  `KeyError` on a fresh run. The committed `Tolima.csv` has prefix-free names, so the script was
  edited after that file was made. The package strips the prefix once, in the catalogue reader.
- **Fixed waits.** The script sleeps `2 * TimeWait` seconds and then opens `datos.zip`. On a slow
  connection the zip is missing or partial; on a fast one the time is wasted.
  `dhime.files.wait_for_file` waits for the file and for Chrome's `.crdownload` to disappear.
- **Download folder.** Files go to the user's Downloads folder (hard-coded `C:/Users/santi/...`),
  mixing with other files, and `extractall` unpacks every member. The package gives Chrome a
  folder of its own and extracts only the expected member.
- **No resume.** An existing `Tolima.csv` is loaded but every station and period is downloaded
  again. The package skips periods that already have values or are marked done in a progress file.
- **Page load timeout.** If the first element does not appear, the script prints a message and
  then fails with `NameError` (`button` was never assigned).
- **Station not found.** The script stops that station (`break`) but leaves the form in
  whatever state it was; the counter `prev` used to find the next confirmation dialog is only
  updated after a successful download. The browser class keeps this behaviour (`_dialogs`) and
  has not been tested against the live portal.
- `all` shadows the Python built-in.

## Observations on the example data

- `Tolima.csv` (14,976 rows, 1980-01-01 to 2020-12-31, 110 columns) and `Tolima - back up .csv`
  are identical. One of them can be removed from the repository (each is 4.3 MB; git history
  keeps it).
- The table has 40 columns that are not in `Datos_Tolima.csv` (70 stations), probably from an
  earlier version of the catalogue; 67 of the 110 columns contain data.
- 251 of the 280 station-period pairs of the catalogue already have data. Four catalogue
  stations have no data at all (`21230110`, `22065040`, `21220040`, `21250110`): they were
  probably not offered by the portal or have no record. Running the package again would
  request the remaining 29 pairs and retry those four.
