"""Chrome driver for the IDEAM DHIME portal (http://dhime.ideam.gov.co/atencionciudadano/).

This module is a port of the steps in ``legacy/Download IDEAM.py`` to the Selenium 4 API. It
needs Selenium (``pip install "dhime[browser]"``) and Chrome. The page locators are collected
in :data:`LOCATORS`: they are the ones the legacy script used in 2022 and were **not** checked
against the current portal (the tests use a fake browser). If the portal changes, only
:data:`LOCATORS` and the few methods below should need edits.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .files import MEMBER, ZIP_NAME, DownloadError, extract_download, wait_for_file

URL = "http://dhime.ideam.gov.co/atencionciudadano/"

LOCATORS = {
    "terms_checkbox": (".checkbox", "css"),
    "terms_accept": (".enable-btn", "css"),
    "date_from": ("datepicker", "id"),
    "date_to": ("datepicker1", "id"),
    "parameter_menu": ("//div[@id='pnlEstandar']/table/tbody/tr/td[2]/span/span/span", "xpath"),
    "parameter_item": ("//li[contains(.,'{parameter}')]", "xpath"),
    "variable_input": ("//input[contains(@onclick,'{variable}')]", "xpath"),
    "department_menu": ("//div[@id='first']/table/tbody/tr/td[2]/span/span/span", "xpath"),
    "department_item": ("//li[contains(.,'{department}')]", "xpath"),
    "department_option": ("//*[@id='deptos2_listbox']/li[{index}]", "xpath"),
    "municipality_menu": ("//div[@id='first']/table/tbody/tr[2]/td[2]/span/span/span", "xpath"),
    "municipality_all": ("//ul[@id='municipio2_listbox']/li[2]", "xpath"),
    "station_input": ("//input[@value='{code}']", "xpath"),
    "station_checkbox": ("//input[@id='checkMetaData{suffix}']", "xpath"),
    "add_query": ("//div[@id='first']/div[5]/div", "xpath"),
    "download_button": ("//div[@id='second']/div/div[3]/div", "xpath"),
    "accept_use": ("dijit_form_Button_2_label", "id"),
    "clear_query": ("//*[@id='second']/div/div[3]/div[3]", "xpath"),
    "confirm_clear": ("//*[@id='dijit_form_Button_{n}_label']", "xpath"),
    "query_tab": ("//*[@id='ContenedorCiudadano_tablist_first']", "xpath"),
}


class DhimeBrowser:
    """Context manager that downloads one station and period at a time.

    Parameters
    ----------
    download_dir : folder where Chrome saves ``datos.zip`` (created; use a folder of its own)
    parameter, variable : DHIME parameter and variable (``PRECIPITACION`` / ``PTPM_CON`` = daily precipitation)
    wait : seconds to wait for page elements; the download itself waits ``4 * wait``
    headless : run Chrome without a window
    """

    def __init__(self, download_dir="downloads", parameter="PRECIPITACION", variable="PTPM_CON", wait=15,
                 headless=False):
        self.download_dir = Path(download_dir).resolve()
        self.parameter, self.variable, self.wait, self.headless = parameter, variable, wait, headless
        self._driver = None
        self._dialogs = 0  # the portal numbers its confirmation dialogs; the legacy script counted them

    # ---- lifecycle -------------------------------------------------------------------
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    def open(self):
        try:
            from selenium import webdriver
        except ImportError as err:
            raise ImportError('Selenium is required for downloads: pip install "dhime[browser]"') from err
        self.download_dir.mkdir(parents=True, exist_ok=True)
        options = webdriver.ChromeOptions()
        options.add_experimental_option("prefs", {"download.default_directory": str(self.download_dir),
                                                  "download.prompt_for_download": False})
        if self.headless:
            options.add_argument("--headless=new")
        self._driver = webdriver.Chrome(options=options)  # Selenium Manager finds the driver
        self._driver.get(URL)
        self._find("terms_checkbox", wait=self.wait * 1.5).click()
        self._find("terms_accept").click()
        self._dialogs = 0

    def close(self):
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    # ---- helpers ---------------------------------------------------------------------
    def _by(self, kind):
        from selenium.webdriver.common.by import By

        return {"css": By.CSS_SELECTOR, "id": By.ID, "xpath": By.XPATH}[kind]

    def _find(self, name, wait=None, **fmt):
        """Element for a locator, waiting for it to be present (``wait`` seconds) or immediately."""
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        value, kind = LOCATORS[name]
        value = value.format(**fmt)
        if wait is None:
            return self._driver.find_element(self._by(kind), value)
        return WebDriverWait(self._driver, wait).until(EC.presence_of_element_located((self._by(kind), value)))

    def _type(self, name, text):
        box = self._find(name, wait=self.wait * 1.5)
        box.click()
        box.clear()
        box.send_keys(text)

    # ---- one download ----------------------------------------------------------------
    def download(self, station, start, end) -> Optional[Path]:
        """Download ``station`` between two dd/mm/yyyy dates; returns the CSV path, or ``None`` if the
        station is not in the portal's list for its department."""
        if self._driver is None:
            raise RuntimeError("Call open() or use the browser as a context manager")
        self._type("date_from", start)
        self._type("date_to", end)
        self._find("parameter_menu").click()
        self._find("parameter_item", parameter=self.parameter).click()
        self._find("variable_input", wait=self.wait, variable=self.variable).click()
        time.sleep(2)
        self._find("department_menu").click()
        time.sleep(self.wait / 2)
        item = self._find("department_item", wait=self.wait, department=station.department)
        index = int(item.get_attribute("outerHTML").split('"')[9]) + 1  # position in the list, as the legacy script
        self._find("department_option", index=index).click()
        time.sleep(self.wait / 4)
        self._find("municipality_menu").click()
        self._find("municipality_all", wait=self.wait).click()
        time.sleep(2)
        try:
            html = self._find("station_input", code=station.code).get_attribute("outerHTML")
            suffix = html.split()[1].replace('"', "").replace("id=idEstacionmetaData", "")
            self._find("station_checkbox", suffix=suffix).click()
        except Exception:  # selenium's NoSuchElementException and malformed markup alike
            return None
        self._find("add_query").click()
        self._find("download_button", wait=self.wait).click()
        self._find("accept_use", wait=self.wait).click()

        zip_path = self.download_dir / ZIP_NAME
        wait_for_file(zip_path, timeout=self.wait * 4)
        name = f"{station.code}-{self.variable}-{start.replace('/', '')}-{end.replace('/', '')}.csv"
        csv = extract_download(zip_path, self.download_dir, name, MEMBER)

        self._find("clear_query").click()
        self._find("confirm_clear", wait=self.wait, n=4 + self._dialogs).click()
        self._dialogs += 2
        self._find("query_tab", wait=self.wait).click()
        return csv
