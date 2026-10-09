import json
from datetime import date, timedelta

DEFAULT_CITIES = {
    "delhi": [{"name": "Delhi", "latitude": 28.65, "longitude": 77.23, "country": "IN", "state": "Delhi"}],
    "london": [{"name": "London", "latitude": 51.5, "longitude": -0.12, "country": "GB", "state": "England"}],
    "mumbai": [{"name": "Mumbai", "latitude": 19.07, "longitude": 72.87, "country": "IN", "state": "Maharashtra"}],
    "singapore": [{"name": "Singapore", "latitude": 1.29, "longitude": 103.85, "country": "SG"}],
}

REVERSE_NAME = "Connaught Place, New Delhi, Delhi, India"


def build_weather(is_day=1, temp=31.4, humidity=62, wind=12.6, cloud=45, pressure=1008.2, start="2026-10-08"):
    first = date.fromisoformat(start)
    days = [(first + timedelta(days=i)).isoformat() for i in range(7)]
    hours = range(168)
    return {
        "current": {
            "is_day": is_day,
            "pressure_msl": pressure,
            "temperature_2m": temp,
            "wind_speed_10m": wind,
            "cloud_cover": cloud,
            "relative_humidity_2m": humidity,
        },
        "hourly": {
            "temperature_2m": [round(20 + 0.5 * (h % 24), 1) for h in hours],
            "relative_humidity_2m": [40 + (h % 24) for h in hours],
            "wind_speed_10m": [round(5 + 0.3 * (h % 24), 1) for h in hours],
            "cloud_cover": [4 * (h % 24) for h in hours],
        },
        "daily": {
            "time": days,
            "temperature_2m_max": [round(34.1 - 0.3 * i, 1) for i in range(7)],
            "temperature_2m_min": [round(24.2 - 0.2 * i, 1) for i in range(7)],
            "sunrise": [f"{d}T06:12" for d in days],
            "sunset": [f"{d}T18:03" for d in days],
            "wind_speed_10m_max": [15.2] * 7,
            "weather_code": [1] * 7,
        },
    }


MOCK_JS = """
(() => {
  const CFG = __CFG__;
  const realFetch = window.fetch.bind(window);
  const reply = (body, status) => new Response(JSON.stringify(body), {
    status: status || 200,
    headers: {"Content-Type": "application/json"}
  });
  window.__fetchLog = [];
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    const handlers = [
      ["api-ninjas.com/v1/geocoding", () => {
        if (CFG.geocode_status !== 200) return reply({error: "mock failure"}, CFG.geocode_status);
        const city = (new URL(url).searchParams.get("city") || "").trim();
        if (city === "") return reply({error: "city required"}, 400);
        return reply(CFG.cities[city.toLowerCase()] || []);
      }],
      ["open-meteo.com", () => reply(CFG.weather_status === 200 ? CFG.weather : {error: "mock failure"}, CFG.weather_status)],
      ["nominatim.openstreetmap.org", () => reply({display_name: CFG.reverse_name})]
    ];
    const match = handlers.find(([key]) => url.includes(key));
    if (!match) return realFetch(input, init);
    window.__fetchLog.push(url);
    return new Promise(resolve => setTimeout(() => resolve(match[1]()), CFG.delay_ms));
  };
  if (CFG.geo) {
    navigator.geolocation.getCurrentPosition = (ok, fail) => setTimeout(() => {
      if (CFG.geo === "denied") {
        if (fail) fail({code: 1, message: "User denied Geolocation"});
      } else {
        ok({coords: {latitude: CFG.geo.lat, longitude: CFG.geo.lon}});
      }
    }, 50);
  }
})();
"""


def install_mock(driver, weather=None, cities=None, weather_status=200, geocode_status=200,
                 geo=None, reverse_name=REVERSE_NAME, delay_ms=0):
    cfg = {
        "cities": cities if cities is not None else DEFAULT_CITIES,
        "weather": weather if weather is not None else build_weather(),
        "weather_status": weather_status,
        "geocode_status": geocode_status,
        "geo": geo,
        "reverse_name": reverse_name,
        "delay_ms": delay_ms,
    }
    source = MOCK_JS.replace("__CFG__", json.dumps(cfg))
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": source})
