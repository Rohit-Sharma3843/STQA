import os
import platform
import re
import time
from datetime import datetime

import pytest
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService

from mock_api import install_mock
from weather_page import BASE_URL, WeatherPage

BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/usr/bin/brave-browser",
]

RESULTS = {}
META = {}


def build_driver():
    browser = os.getenv("BROWSER", "edge").strip().lower()
    binary = os.getenv("BROWSER_PATH", "").strip()
    driver_path = os.getenv("DRIVER_PATH", "").strip()
    if browser == "edge":
        options = webdriver.EdgeOptions()
        factory, service_class = webdriver.Edge, EdgeService
    else:
        options = webdriver.ChromeOptions()
        factory, service_class = webdriver.Chrome, ChromeService
    if browser == "brave" and not binary:
        binary = next((p for p in BRAVE_PATHS if os.path.exists(p)), "")
        if not binary:
            raise RuntimeError("Brave not found. Set BROWSER_PATH to the full path of brave.exe")
    if binary:
        options.binary_location = binary
    if os.getenv("HEADLESS", "0").strip() == "1":
        options.add_argument("--headless=new")
    if os.getenv("NO_SANDBOX", "0").strip() == "1":
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=en-US")
    service = service_class(executable_path=driver_path) if driver_path else service_class()
    return factory(options=options, service=service)


@pytest.fixture
def driver():
    drv = build_driver()
    drv.implicitly_wait(0)
    if "browser" not in META:
        caps = drv.capabilities
        name = os.getenv("BROWSER", "edge").strip().lower()
        META["browser"] = f"{name.capitalize()} (engine: {caps.get('browserName', '')} {caps.get('browserVersion', '')})"
    yield drv
    drv.quit()


@pytest.fixture
def make_page(driver):
    def _make(mock=True, **mock_options):
        if mock:
            install_mock(driver, **mock_options)
        page = WeatherPage(driver, BASE_URL)
        page.open()
        return page

    return _make


def pytest_sessionstart(session):
    META["started_at"] = datetime.now()
    META["clock"] = time.perf_counter()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        longrepr = report.longrepr
        if report.outcome == "skipped" and isinstance(longrepr, tuple):
            message = str(longrepr[2]).replace("Skipped: ", "")
        else:
            message = getattr(getattr(longrepr, "reprcrash", None), "message", "") or ""
        message = message.strip().splitlines()[0] if message.strip() else ""
        message = re.sub(r"^(selenium\.common\.exceptions\.)?(TimeoutException: Message: |AssertionError: |[A-Za-z]+Exception: Message: )", "", message)[:240]
        RESULTS[item.name] = {
            "name": item.name,
            "outcome": report.outcome,
            "duration": report.duration,
            "message": message,
            "screenshot": None,
        }
    if report.when != "call" or not report.failed:
        return
    drv = item.funcargs.get("driver")
    if drv is None:
        return
    try:
        folder = os.path.join(str(item.config.rootpath), "reports", "screenshots")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, re.sub(r"[^A-Za-z0-9_.-]", "_", item.name) + ".png")
        drv.save_screenshot(path)
        RESULTS[item.name]["screenshot"] = path
        from pytest_html import extras
        report.extras = getattr(report, "extras", []) + [extras.png(drv.get_screenshot_as_base64())]
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    try:
        import make_pdf_report
    except ImportError:
        print("\nPDF report skipped: run  pip install reportlab  to enable it.")
        return
    started = META.get("started_at", datetime.now())
    seconds = time.perf_counter() - META.get("clock", time.perf_counter())
    url = BASE_URL
    if "localhost" in url or "127.0.0.1" in url:
        note = "Run against a local copy of the application code. The weather services were replaced with fixed test data."
    else:
        note = "Tests marked live used the real site and services. All other tests used fixed data in place of the weather services."
    meta = {
        "app_url": url,
        "browser": META.get("browser", ""),
        "os": platform.platform(),
        "tools": f"Python {platform.python_version()} / Selenium {selenium.__version__} / pytest {pytest.__version__}",
        "started": started.strftime("%d-%b-%Y %H:%M"),
        "duration": f"{seconds / 60:.1f} minutes" if seconds >= 120 else f"{seconds:.0f} seconds",
        "note": note,
    }
    out = os.path.join(str(session.config.rootpath), "reports", "Test_Report.pdf")
    try:
        make_pdf_report.build(list(RESULTS.values()), meta, out)
        print(f"\nPDF test report: {out}")
    except Exception as error:
        print(f"\nPDF report could not be created: {error}")
