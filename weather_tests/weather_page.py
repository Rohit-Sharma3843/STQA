import os

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("BASE_URL", "https://weather-puce-six.vercel.app/").strip()
ERROR_TEXT = "Error in fetching data"

HOURLY_BUTTONS = {
    "temperature": "hourly_temp",
    "wind": "hourly_w_speed",
    "cloud": "hourly_c_cover",
    "humidity": "hourly_humidity",
}


class WeatherPage:
    HEADING = (By.ID, "heading")
    CITY = (By.ID, "city")
    SEARCH = (By.ID, "search_button")
    LOCATE = (By.ID, "curr_loc")
    HISTORY_ITEMS = (By.CSS_SELECTOR, "#history .history")
    PANEL = (By.ID, "today")
    PLACE = (By.ID, "search_val")
    CURR_TEMP = (By.ID, "curr_temp")
    HUMIDITY = (By.ID, "hum_val")
    WIND = (By.ID, "w_speed_val")
    CLOUD = (By.ID, "cloud_val")
    PRESSURE = (By.ID, "pressure_now")
    WEATHER_ICON = (By.CSS_SELECTOR, "#weather_img img")
    MAIN_STATS = (By.ID, "main_stats")
    PREV = (By.ID, "prev")
    NEXT = (By.ID, "next")
    GET7 = (By.ID, "get7")
    DAILY = (By.ID, "daily")

    def __init__(self, driver, url=BASE_URL, timeout=15):
        self.driver = driver
        self.url = url
        self.timeout = timeout

    def wait(self, timeout=None):
        return WebDriverWait(self.driver, timeout or self.timeout)

    def open(self):
        self.driver.get(self.url)
        self.wait().until(EC.visibility_of_element_located(self.CITY))
        self.wait().until(lambda d: d.execute_script(
            "const h = document.getElementById('head');"
            "return h.getBoundingClientRect().left >= 0 && getComputedStyle(h).opacity === '1';"
        ))

    def find(self, locator):
        return self.driver.find_element(*locator)

    def shown(self, locator):
        try:
            return self.find(locator).is_displayed()
        except NoSuchElementException:
            return False

    def value(self, locator):
        return (self.find(locator).get_attribute("textContent") or "").strip()

    def panel_text(self):
        return self.find(self.PANEL).text

    def click(self, locator):
        element = self.wait().until(EC.presence_of_element_located(locator))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        self.wait().until(EC.element_to_be_clickable(locator)).click()

    def type_city(self, text):
        field = self.find(self.CITY)
        field.clear()
        if text:
            field.send_keys(text)

    def search(self, city):
        self.type_city(city)
        self.click(self.SEARCH)

    def wait_result(self, timeout=None):
        def ready(_):
            if not self.shown(self.PANEL):
                return False
            if ERROR_TEXT in self.panel_text():
                raise AssertionError(f"Expected weather data but the page shows '{ERROR_TEXT}'")
            return self.value(self.PLACE) not in ("", "Place")

        self.wait(timeout).until(ready)

    def wait_error(self, timeout=None):
        self.wait(timeout).until(
            lambda _: self.shown(self.PANEL) and ERROR_TEXT in self.panel_text(),
            message=f"'{ERROR_TEXT}' was not shown",
        )

    def wait_for_place(self, text, timeout=None, message=None):
        self.wait(timeout).until(lambda _: text in self.value(self.PLACE), message=message)

    def open_hourly(self, key):
        self.click((By.ID, HOURLY_BUTTONS[key]))
        self.wait().until(EC.visibility_of_element_located(self.MAIN_STATS))

    def hourly_rows(self):
        rows = []
        for i in range(1, 9):
            time_label = self.value((By.CSS_SELECTOR, f"#stat{i} .time"))
            reading = self.value((By.CSS_SELECTOR, f"#stat{i} > span"))
            rows.append((time_label, reading))
        return rows

    def stat_heading(self):
        return self.value((By.CSS_SELECTOR, "#stat .hourly_parameter"))

    def daily_cards(self):
        cards = []
        for card in self.driver.find_elements(By.CSS_SELECTOR, ".days"):
            texts = lambda css: [
                e.get_attribute("textContent").strip() for e in card.find_elements(By.CSS_SELECTOR, css)
            ]
            labels = texts(".daily_stat_names p")
            values = texts(".daily_stat_values p")
            cards.append({
                "date": card.find_element(By.CSS_SELECTOR, ".date").get_attribute("textContent").strip(),
                "values": dict(zip(labels, values)),
            })
        return cards
