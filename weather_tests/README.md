# Weather App - Automated Test Suite

Tests for https://weather-puce-six.vercel.app/ using Selenium WebDriver (Python + pytest) and a Selenium IDE project.

## What is in this folder

| File | Purpose |
|---|---|
| `test_weather_app.py` | 29 test scenarios (40 test runs with parameters) - the regression suite |
| `weather_page.py` | Page object: locators and helper actions for the app |
| `mock_api.py` | Replaces the geocoding, forecast and reverse-geocoding calls so results are predictable |
| `conftest.py` | Browser setup (Edge, Brave or Chrome), screenshots on failure, creates the PDF report after the run |
| `make_pdf_report.py` | Builds `reports\Test_Report.pdf` from the results |
| `pytest.ini` | Test markers and the HTML report setting |
| `weather_app.side` | Selenium IDE project (8 recorded-style tests + 1 suite) |
| `TEST_PLAN.md` | Test plan, bug taxonomy, regression approach, exploratory testing and defect list |

## 1. Set up (once)

1. Install Python 3.10 or newer (tick "Add Python to PATH" in the installer).
2. Open Command Prompt in this folder and run:

```
pip install -r requirements.txt
```

Selenium 4 downloads the correct browser driver for Edge or Chrome by itself. Keep the browser up to date.

## 2. Run the tests (Selenium WebDriver)

```
python -m pytest
```

This opens Microsoft Edge (the default) and runs everything. When it finishes, two reports are created in the `reports` folder:

- `reports\Test_Report.pdf` - the PDF test report (summary, environment, results table, defects with screenshots, exploratory testing, conclusion)
- `reports\test_report.html` - a detailed HTML report with a screenshot for each failed test

To add your own findings from manual exploratory sessions to the PDF, edit the `SESSION_NOTES` list near the top of `make_pdf_report.py` (one entry per session with `session`, `charter`, `duration` and `notes`) and run the tests again.

| Goal | Command |
|---|---|
| Use Brave | `set BROWSER=brave` then `python -m pytest` |
| Brave in a custom folder | `set BROWSER_PATH=C:\path\to\brave.exe` first |
| Use Chrome | `set BROWSER=chrome` then `python -m pytest` |
| Hide the browser window | `set HEADLESS=1` first |
| Quick sanity check only | `python -m pytest -m smoke` |
| Normal regression run (skip known defects) | `python -m pytest -m "not bug"` |
| Only the tests that expose known defects | `python -m pytest -m bug` |
| Only tests against the real internet | `python -m pytest -m live` |
| One test | `python -m pytest -k tc12` |
| Test a local copy of your code | `set BASE_URL=http://localhost:8000/` (start it with `python -m http.server 8000` in your project folder) |

On PowerShell use `$env:BROWSER="brave"` instead of `set BROWSER=brave`.

## How to read the results

- **Passed**: the app behaves as expected.
- **Failed**: a defect was found, or the app or network was unavailable. Open the screenshot in the report and read the message, which says what is wrong.
- Tests marked `bug` are written to expose known defects, so they are expected to fail until the defect is fixed. When you fix one, it turns green and becomes a regression test.
- Most tests replace the weather services with fixed data (through the browser's DevTools), so results do not depend on the internet or on API limits. Tests marked `live` (TC01 to TC03) use the real site and real services.

## 3. Run the Selenium IDE project

1. Install the **Selenium IDE** extension from the Edge Add-ons store (Edge) or the Chrome Web Store (Brave).
2. Open the extension and choose **Open an existing project**.
3. Select `weather_app.side` from this folder.
4. Choose the suite **Weather Regression Suite** and click **Run all tests in suite** (or run one test with the play button).
5. The log pane shows each command and a pass or fail result. These tests call the real site, so they need internet.

To record your own test: **Record a new test in a new project**, enter the site URL, use the app, then click the red button to stop and save.

Optional command line run (needs Node.js): `npm install -g selenium-side-runner` and then `selenium-side-runner -c "browserName=MicrosoftEdge" weather_app.side`.

## 4. Exploratory testing and the final report

Use the charters and session notes template in `TEST_PLAN.md` while you explore the app by hand (about 30 minutes per charter). Add what you find to the defect list, and attach `reports/test_report.html` as the automated test report.

## Troubleshooting

- **"session not created" or version error**: update Edge, Brave or Chrome to the latest version and run `pip install -U selenium`.
- **Brave not found**: set `BROWSER_PATH` to the full path of `brave.exe`.
- **Tests time out on the live site**: check your internet connection. The live site depends on the third-party weather services.
