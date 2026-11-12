import importlib.util

import pytest

from dhime import browser, cli

HAS_SELENIUM = importlib.util.find_spec("selenium") is not None


def test_dry_run_lists_the_requests_without_opening_a_browser(capsys, tmp_path):
    (tmp_path / "c.csv").write_text("Codigo;Dpto;Lat;Long;Elevation\npr_1;A;1;1;1\npr_2;B;2;2;2\n")
    code = cli.main(["--catalog", str(tmp_path / "c.csv"), "--output", str(tmp_path / "o.csv"), "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0 and "2 stations x 4 periods = 8 requests" in out and "01/01/1980 -> 01/01/1990" in out


def test_parser_defaults_match_the_legacy_script():
    a = cli.build_parser().parse_args(["--catalog", "c", "--output", "o"])
    assert (a.parameter, a.variable, a.wait, a.headless) == ("PRECIPITACION", "PTPM_CON", 15, False)
    assert a.boundaries == ["01/01/1980", "01/01/1990", "01/01/2000", "01/01/2010", "31/12/2020"]


def test_every_locator_template_can_be_filled():
    values = dict(parameter="P", variable="V", department="D", index=3, code="1", suffix="2", n=4)
    for name, (template, kind) in browser.LOCATORS.items():
        assert kind in {"css", "id", "xpath"}
        assert "{" not in template.format(**values), name


def test_download_needs_an_open_browser():
    with pytest.raises(RuntimeError):
        browser.DhimeBrowser().download(None, "01/01/2000", "01/01/2001")


@pytest.mark.skipif(HAS_SELENIUM, reason="would start Chrome")
def test_open_explains_how_to_install_selenium(tmp_path):
    with pytest.raises(ImportError, match=r"dhime\[browser\]"):
        browser.DhimeBrowser(tmp_path).open()
