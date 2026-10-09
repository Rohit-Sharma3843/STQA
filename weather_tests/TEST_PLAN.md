# Test Plan - Weather Forecast Web App

## 1. Objective and scope

Check that the Weather Forecast web app (https://weather-puce-six.vercel.app/) lets a user search a city or use their location and read the current weather, a 24-hour forecast and a 7-day forecast correctly, and that it handles errors and small screens well.

**Out of scope:** accuracy of the weather data itself (it comes from the Open-Meteo service), and the third-party services' own availability.

## 2. Application and environment

| Item | Detail |
|---|---|
| Application | Static web app: HTML, CSS and JavaScript (no framework), hosted on Vercel |
| External services | API Ninjas (city to coordinates), Open-Meteo (forecast), OpenStreetMap Nominatim (location name) |
| Browsers | Microsoft Edge and Brave (latest); Chrome as extra check |
| Tools | Selenium WebDriver 4 with Python and pytest, Selenium IDE, pytest-html reports |
| Test data | Cities: Delhi, London, Mumbai, Singapore (no state); invalid inputs: empty, digits, symbols, spaces, script text |

## 3. Features to be tested

| Feature | Test cases |
|---|---|
| Page load and layout | TC01, TC02 |
| City search with valid city | TC03, TC04, TC05, TC06 |
| 24-hour forecast (4 parameters, paging) | TC07, TC08, TC09, TC10 |
| 7-day forecast | TC11, TC12, TC13 |
| Invalid input and error handling | TC14, TC15, TC16, TC25, TC29 |
| Search history suggestions | TC17, TC18, TC19 |
| Keyboard use | TC20 |
| Location display | TC21, TC23 |
| Use my current location | TC22, TC24 |
| Responsive layout | TC26 |
| Security | TC27, TC29 |
| Accessibility | TC28 |

## 4. Test approach

- **Smoke tests** (`-m smoke`): page opens and a search returns weather.
- **Regression tests** (`-m regression`): every feature above is rechecked after each code change.
- **Negative tests** (`-m negative`): invalid input, permission denied, service failure.
- **Exploratory testing**: manual, time-boxed sessions with charters (section 7).
- **Test design techniques**: equivalence classes and boundary values (first and last hourly page, 5-item history limit), error guessing, state-based checks (state after an error).
- Services are replaced by fixed data in most tests, so a failure points to the app and not to the internet.

## 5. Bug taxonomy

| Category | What it covers | Example in this app |
|---|---|---|
| Functional | Feature does not do what it should | Search does not work after an error (D2) |
| Data / display accuracy | Wrong or badly formatted values | Min and Max swapped (D1), "undefined" in place name (D4) |
| Error handling | No or poor feedback on failure | Silent failure when forecast service is down (D7) |
| UI / usability | Layout, controls, keyboard | Enter key does nothing (D3), buttons never look disabled (D10) |
| Compatibility / responsive | Browser and screen size problems | Checked at 375 and 768 px (TC26) |
| Performance | Slow load or response | Page load time under 5 seconds (TC02) |
| Security | Data exposure, injection | API key visible in client script (D8) |
| Accessibility | Use with assistive technology | Buttons with no accessible name (D9) |
| Code quality | Hidden risks in the code | See section 8 |

**Severity:** Critical (app unusable or data exposed), Major (feature broken, workaround exists), Minor (cosmetic or small inconvenience).

## 6. Regression testing

1. Run `python -m pytest -m "not bug"` after every change: all tests must pass.
2. Run `python -m pytest -m bug` to see which known defects are still open.
3. When a defect is fixed its test passes; the `bug` marker can then be changed to `regression`.
4. Run the Selenium IDE suite on the live site as a final smoke check before release.

Exit criteria: all regression tests pass, no open Critical or Major defects, and the HTML report is attached.

## 7. Exploratory testing

Each session is about 30 minutes. Write notes while you test.

| Charter | Ideas to try |
|---|---|
| E1: Explore search with unusual inputs | Very long names, cities with spaces, accents, `&` and `#` characters, lower and upper case, same city twice, two quick searches |
| E2: Explore the forecast screens | Compare values with another weather site, switch parameters quickly, go back and forth between pages, open the 7-day view and search another city |
| E3: Explore location and permissions | Allow, block, then allow again; location on a desktop with no GPS; offline mode |
| E4: Explore screen sizes and browsers | 320, 375, 768, 1366 px, zoom 150 percent, Edge and Brave |
| E5: Explore failure situations | Turn off the network after the page loads, throttle the connection, block a service |

**Session notes template**

| Session | Charter | Tester | Date | Duration | Notes / what was observed | Defects found |
|---|---|---|---|---|---|---|
| S1 | E1 | | | | | |

## 8. Defects found

These came from running the suite against a copy of the source code with fixed service data, and from reading the code. Confirm each one on the live site by running the suite there.

| ID | Test | Defect | Category | Severity |
|---|---|---|---|---|
| D1 | TC12 | In the 7-day cards the labels read Min then Max, but the values are in the opposite order, so "Min" shows the higher temperature | Data accuracy | Major |
| D2 | TC16 | After an empty or invalid search, the weather panel is replaced by the error text and a later valid search never shows weather again until the page is reloaded | Functional | Major |
| D3 | TC20 | Pressing Enter in the search box does nothing | UI / usability | Minor |
| D4 | TC21 | A city with no state shows "Singapore, undefined, SG" | Data display | Minor |
| D5 | TC23 | Location from the "use my current location" button ends with ", ," | Data display | Minor |
| D6 | TC24 | If location permission is denied, the button stays on "Searching.." and the search button stays hidden | Error handling | Major |
| D7 | TC25 | If the forecast service fails, the user sees nothing | Error handling | Major |
| D8 | TC27 | An API key is written in `source.js`, visible to every visitor. It should be moved to a server function and replaced with a new key | Security | Critical |
| D9 | TC28 | The search button and the previous and next buttons have no accessible name | Accessibility | Minor |
| D10 | TC10 | Previous and Next never look disabled (the code sets `disabled` on the image inside the button, not on the button) | UI / usability | Minor |

**Code review observations (not automated; check them during exploratory testing)**

- The "24-Hour Forecast" always starts at 00:00 of today, not at the current hour.
- The heading says "Relative humidity" while the button says "Relative Humidity".
- Dates in the 7-day view are shown as 2026-10-08, while the page design uses 27/08/2025.
- The city name is placed in the request URL without encoding, so names containing `&` or `#` may be cut short.
- Event handlers for the hourly buttons are added again after every search.
- `country` is used without being declared, and `findHistoryElem` is called but never defined.
- The HTML has a `<head>` inside `<body>` and a `<meta http-equiv>` with no content.
- The page loads about 14 Google font families, which slows the first load.
