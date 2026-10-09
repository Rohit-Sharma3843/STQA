import re
import time

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from mock_api import build_weather
from weather_page import BASE_URL, ERROR_TEXT, WeatherPage


def fmt(value):
    return str(int(value)) if float(value).is_integer() else str(value)


def number(text):
    return float(re.search(r"-?\d+(?:\.\d+)?", text).group())


def searched(make_page, city="Delhi", **mock_options):
    page = make_page(**mock_options)
    page.search(city)
    page.wait_result()
    return page


@pytest.mark.smoke
@pytest.mark.live
def test_tc01_home_page_loads(make_page):
    page = make_page(mock=False)
    assert page.driver.title == "Weather Forecast"
    assert page.value(page.HEADING) == "Weather Forecast"
    assert page.find(page.CITY).get_attribute("placeholder") == "enter the city name"
    assert page.shown(page.SEARCH)
    assert page.shown(page.LOCATE)
    assert not page.shown(page.PANEL)


@pytest.mark.live
def test_tc02_page_load_time(driver):
    limit = 5.0
    start = time.perf_counter()
    driver.get(BASE_URL)
    elapsed = time.perf_counter() - start
    print(f"\nPage load time: {elapsed:.2f}s (limit {limit}s)")
    assert elapsed <= limit


@pytest.mark.smoke
@pytest.mark.live
def test_tc03_live_search_real_city(make_page):
    page = make_page(mock=False)
    page.search("London")
    page.wait_result(timeout=30)
    assert "London" in page.value(page.PLACE)


@pytest.mark.smoke
@pytest.mark.regression
def test_tc04_search_valid_city_shows_weather(make_page):
    page = searched(make_page, "Delhi")
    assert "Delhi" in page.value(page.PLACE)
    assert page.value(page.CURR_TEMP) == "31.4°C"


@pytest.mark.regression
def test_tc05_current_conditions_match_api_data(make_page):
    page = searched(make_page, "Delhi")
    assert page.value(page.HUMIDITY) == "62"
    assert page.value(page.WIND) == "12.6"
    assert page.value(page.CLOUD) == "45"
    assert page.value(page.PRESSURE) == "1008.2"


@pytest.mark.regression
@pytest.mark.parametrize("is_day, image", [(1, "day.png"), (0, "night.png")])
def test_tc06_day_night_icon(make_page, is_day, image):
    page = searched(make_page, "Delhi", weather=build_weather(is_day=is_day))
    assert page.find(page.WEATHER_ICON).get_attribute("src").endswith(image)


@pytest.mark.regression
@pytest.mark.parametrize("key, heading", [
    ("temperature", "temperature"),
    ("wind", "wind speed"),
    ("cloud", "cloud cover"),
    ("humidity", "relative humidity"),
])
def test_tc07_hourly_buttons_switch_heading(make_page, key, heading):
    page = searched(make_page)
    page.open_hourly(key)
    assert page.stat_heading().lower() == heading


@pytest.mark.regression
def test_tc08_hourly_temperature_pagination(make_page):
    page = searched(make_page)
    page.open_hourly("temperature")

    def window(start):
        return [(f"{h:02d}00", fmt(round(20 + 0.5 * (h % 24), 1)) + "°C") for h in range(start, start + 8)]

    assert page.hourly_rows() == window(0)
    page.click(page.NEXT)
    assert page.hourly_rows() == window(8)
    page.click(page.NEXT)
    assert page.hourly_rows() == window(16)
    page.click(page.NEXT)
    assert page.hourly_rows() == window(16)
    page.click(page.PREV)
    page.click(page.PREV)
    assert page.hourly_rows() == window(0)
    page.click(page.PREV)
    assert page.hourly_rows() == window(0)


@pytest.mark.regression
@pytest.mark.parametrize("key, unit", [("temperature", "°C"), ("wind", "km/h"), ("cloud", "%"), ("humidity", "%")])
def test_tc09_hourly_values_carry_units(make_page, key, unit):
    page = searched(make_page)
    page.open_hourly(key)
    rows = page.hourly_rows()
    assert len(rows) == 8
    assert all(reading.endswith(unit) for _, reading in rows)


@pytest.mark.bug
@pytest.mark.regression
def test_tc10_boundary_buttons_are_disabled(make_page):
    page = searched(make_page)
    page.open_hourly("temperature")
    prev_button, next_button = page.driver.find_elements(By.CSS_SELECTOR, ".stats_button")
    assert not prev_button.is_enabled(), "Previous button should be disabled on the first page"
    page.click(page.NEXT)
    page.click(page.NEXT)
    assert not next_button.is_enabled(), "Next button should be disabled on the last page"


@pytest.mark.regression
def test_tc11_seven_day_forecast(make_page):
    page = searched(make_page)
    assert not page.shown(page.DAILY)
    page.click(page.GET7)
    assert page.shown(page.DAILY)
    cards = page.daily_cards()
    assert len(cards) == 7
    assert len({card["date"] for card in cards}) == 7


@pytest.mark.bug
@pytest.mark.regression
def test_tc12_daily_min_is_not_greater_than_max(make_page):
    page = searched(make_page)
    page.click(page.GET7)
    for card in page.daily_cards():
        low, high = number(card["values"]["Min"]), number(card["values"]["Max"])
        assert low <= high, f"{card['date']}: Min shows {low} but Max shows {high}"


@pytest.mark.regression
def test_tc13_sunrise_and_sunset_format(make_page):
    page = searched(make_page)
    page.click(page.GET7)
    assert page.value((By.ID, "sunrise_day1")) == "06:12 hrs"
    assert page.value((By.ID, "sunset_day1")) == "18:03 hrs"


@pytest.mark.negative
def test_tc14_empty_search_shows_error(make_page):
    page = make_page()
    page.search("")
    page.wait_error()


@pytest.mark.negative
@pytest.mark.parametrize("city", ["zzzzqq", "12345", "!!!@@@", "   "])
def test_tc15_invalid_city_shows_error(make_page, city):
    page = make_page()
    page.search(city)
    page.wait_error()


@pytest.mark.bug
@pytest.mark.negative
def test_tc16_app_recovers_after_error(make_page):
    page = make_page()
    page.search("zzzzqq")
    page.wait_error()
    page.search("Delhi")
    page.wait_for_place("Delhi", timeout=8, message="A valid search after an error does not show weather any more")


@pytest.mark.regression
def test_tc17_search_history_suggestions(make_page):
    page = searched(make_page, "Delhi")
    page.search("Mumbai")
    page.wait_for_place("Mumbai")
    page.type_city("del")
    items = page.driver.find_elements(*page.HISTORY_ITEMS)
    assert len(items) == 1 and "Delhi" in items[0].text
    ActionChains(page.driver).move_to_element(items[0]).click().perform()
    assert page.find(page.CITY).get_attribute("value") == "Delhi"
    assert page.driver.find_elements(*page.HISTORY_ITEMS) == []


@pytest.mark.regression
def test_tc18_search_history_survives_reload(make_page):
    page = searched(make_page, "Delhi")
    page.driver.refresh()
    page.wait().until(lambda _: page.shown(page.CITY))
    page.type_city("del")
    assert len(page.driver.find_elements(*page.HISTORY_ITEMS)) == 1


@pytest.mark.regression
def test_tc19_search_history_limited_to_five(make_page):
    page = make_page()
    page.driver.execute_script(
        "for (let i = 1; i <= 7; i++) localStorage.setItem('City' + i, "
        "JSON.stringify({loc: 'City' + i, st: 'S', nation: 'N', temp: 20}));"
    )
    page.type_city("city")
    assert len(page.driver.find_elements(*page.HISTORY_ITEMS)) == 5


@pytest.mark.bug
@pytest.mark.regression
def test_tc20_enter_key_starts_search(make_page):
    page = make_page()
    page.find(page.CITY).send_keys("Delhi", Keys.ENTER)
    page.wait(5).until(lambda _: page.shown(page.PANEL), message="Pressing Enter in the search box does not start a search")


@pytest.mark.bug
@pytest.mark.regression
def test_tc21_missing_state_is_not_shown_as_undefined(make_page):
    page = searched(make_page, "Singapore")
    assert "undefined" not in page.value(page.PLACE)


@pytest.mark.regression
def test_tc22_current_location_success(make_page):
    page = make_page(geo={"lat": 28.63, "lon": 77.22})
    page.click(page.LOCATE)
    page.wait_for_place("New Delhi", timeout=10)
    assert page.value(page.LOCATE) == "Use my current location"


@pytest.mark.bug
@pytest.mark.regression
def test_tc23_current_location_text_has_no_trailing_commas(make_page):
    page = make_page(geo={"lat": 28.63, "lon": 77.22})
    page.click(page.LOCATE)
    page.wait_for_place("New Delhi", timeout=10)
    assert not page.value(page.PLACE).rstrip().endswith(","), page.value(page.PLACE)


@pytest.mark.bug
@pytest.mark.negative
def test_tc24_location_permission_denied_recovers(make_page):
    page = make_page(geo="denied")
    page.click(page.LOCATE)
    page.wait(5).until(
        lambda _: page.value(page.LOCATE) == "Use my current location" and page.shown(page.SEARCH),
        message="After location is denied the button stays on 'Searching..' and the search button stays hidden",
    )


@pytest.mark.bug
@pytest.mark.negative
def test_tc25_forecast_api_failure_shows_error(make_page):
    page = make_page(weather_status=500)
    page.search("Delhi")
    page.wait(5).until(
        lambda _: page.shown(page.PANEL) and ERROR_TEXT in page.panel_text(),
        message="No error is shown to the user when the forecast service fails",
    )


@pytest.mark.regression
@pytest.mark.parametrize("width", [375, 768])
def test_tc26_layout_fits_small_screens(make_page, width):
    page = make_page()
    page.driver.set_window_size(width, 900)
    page.search("Delhi")
    page.wait_result()
    page.click(page.GET7)
    overflowing = page.driver.execute_script(
        """
        const limit = window.innerWidth + 2;
        return ['#search', '#today', '.days', '#hourly_buttons']
          .filter(sel => Array.from(document.querySelectorAll(sel)).some(el => {
            const r = el.getBoundingClientRect();
            return r.right > limit || r.left < -2;
          }));
        """
    )
    assert overflowing == [], f"Elements wider than the {width}px screen: {overflowing}"


@pytest.mark.bug
def test_tc27_no_api_key_hardcoded_in_client_script(make_page):
    page = make_page(mock=False)
    source = page.driver.execute_async_script(
        "const done = arguments[arguments.length - 1];"
        "fetch('source.js').then(r => r.text()).then(done);"
    )
    assert not re.search(r"api[_-]?key\s*[=:]\s*[\"'][A-Za-z0-9+/=_-]{16,}", source, re.I), \
        "An API key is hard-coded in source.js and visible to every visitor"


@pytest.mark.bug
def test_tc28_icon_only_buttons_have_accessible_names(make_page):
    page = make_page()
    unnamed = page.driver.execute_script(
        """
        return Array.from(document.querySelectorAll('button'))
          .filter(b => !((b.getAttribute('aria-label') || '').trim()
                         || b.innerText.trim()
                         || (b.querySelector('img') || {}).alt))
          .map(b => b.id || b.className || 'button');
        """
    )
    assert unnamed == [], f"Buttons without an accessible name: {unnamed}"


@pytest.mark.negative
def test_tc29_script_in_search_box_is_not_executed(make_page):
    page = make_page()
    page.search('<img src=x onerror="window.__xss=1">')
    page.wait_error()
    assert page.driver.execute_script("return window.__xss || null;") is None
