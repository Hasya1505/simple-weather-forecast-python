from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)

API_KEY = "5490d2b4b39c33a608fc3a3e931dbf5e"
CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AQI_URL = "http://api.openweathermap.org/data/2.5/air_pollution"


def unix_to_time(unix_ts):
    """Convert Unix timestamp to HH:MM:SS (24-hr)."""
    return datetime.fromtimestamp(unix_ts).strftime('%H:%M:%S')


def aqi_to_text(aqi_value: int) -> str:
    """Convert numeric AQI to simple text."""
    mapping = {
        1: "Good 😀",
        2: "Fair 🙂",
        3: "Moderate 😐",
        4: "Poor 😷",
        5: "Very Poor 🚫",
    }
    return mapping.get(aqi_value, "Unknown")


def clothing_suggestion(temp: float, description: str) -> str:
    """Simple clothing suggestion based on temperature & condition."""
    if "rain" in description:
        return "Carry an umbrella ☔"
    if temp < 10:
        return "Wear a warm jacket 🧥"
    elif temp < 20:
        return "Light jacket or hoodie is good 🧣"
    elif temp < 28:
        return "Comfortable casual clothes 😊"
    else:
        return "It's hot! Wear light clothes & drink water 🥤"


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None
    city_query = ""
    forecast = None
    aqi = None

    if request.method == "POST":
        city_query = request.form.get("city", "").strip()

        if city_query:
            params = {
                "q": city_query,
                "appid": API_KEY,
                "units": "metric"
            }

            try:
                # === CURRENT WEATHER CALL ===
                resp = requests.get(CURRENT_URL, params=params, timeout=5)

                if resp.status_code == 200:
                    data = resp.json()

                    main = data["main"]
                    weather_info = data["weather"][0]
                    wind = data["wind"]
                    sys = data["sys"]

                    # ---- Basic weather information ----
                    temperature = main["temp"]
                    feels_like = main["feels_like"]
                    humidity = main["humidity"]
                    pressure = main["pressure"]
                    visibility_km = round(data.get("visibility", 0) / 1000, 1)
                    description = weather_info["description"].capitalize()
                    wind_speed = wind["speed"]
                    country = sys.get("country", "")

                    sunrise = unix_to_time(sys["sunrise"])
                    sunset = unix_to_time(sys["sunset"])

                    # === Feature 1: ICON URL ===
                    icon_code = weather_info["icon"]  # e.g. "10d"
                    icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"

                    # === Feature 3: LOCAL TIME OF CITY ===
                    timezone_shift = data.get("timezone", 0)  # in seconds
                    current_utc_ts = data.get("dt", 0)
                    local_ts = current_utc_ts + timezone_shift
                    local_time = datetime.utcfromtimestamp(local_ts).strftime("%H:%M:%S")

                    # === Feature 5: BACKGROUND THEME BASED ON WEATHER ===
                    desc_lower = weather_info["description"].lower()
                    if "rain" in desc_lower:
                        theme = "rain"
                    elif "cloud" in desc_lower:
                        theme = "cloud"
                    elif "storm" in desc_lower or "thunder" in desc_lower:
                        theme = "storm"
                    elif "snow" in desc_lower:
                        theme = "snow"
                    else:
                        theme = "clear"

                    # === Feature 8: CLOTHING SUGGESTION ===
                    suggestion = clothing_suggestion(temperature, desc_lower)

                    # coords for forecast + AQI
                    coord = data.get("coord", {})
                    lat = coord.get("lat")
                    lon = coord.get("lon")

                    weather = {
                        "city_name": f"{city_query.capitalize()}, {country}",
                        "temperature": temperature,
                        "feels_like": feels_like,
                        "humidity": humidity,
                        "pressure": pressure,
                        "visibility": visibility_km,
                        "description": description,
                        "wind_speed": wind_speed,
                        "sunrise": sunrise,
                        "sunset": sunset,
                        "icon_url": icon_url,
                        "local_time": local_time,
                        "theme": theme,
                        "suggestion": suggestion,
                    }

                    # === Feature 2: 5-DAY FORECAST (every 24h) ===
                    forecast = []
                    if lat is not None and lon is not None:
                        try:
                            f_params = {
                                "lat": lat,
                                "lon": lon,
                                "appid": API_KEY,
                                "units": "metric"
                            }
                            f_resp = requests.get(FORECAST_URL, params=f_params, timeout=5)
                            if f_resp.status_code == 200:
                                f_data = f_resp.json()
                                f_list = f_data.get("list", [])

                                # Data every 3 hours; pick every 8th entry ≈ next 5 days
                                for i in range(0, min(len(f_list), 40), 8):
                                    item = f_list[i]
                                    dt_txt = item.get("dt_txt", "")
                                    try:
                                        date_obj = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
                                        date_str = date_obj.strftime("%d %b")
                                    except ValueError:
                                        date_str = dt_txt

                                    fw = item["weather"][0]
                                    forecast.append({
                                        "date": date_str,
                                        "temp": round(item["main"]["temp"], 1),
                                        "description": fw["description"].capitalize(),
                                        "icon": f"http://openweathermap.org/img/wn/{fw['icon']}@2x.png",
                                    })
                        except requests.RequestException:
                            # forecast error: ignore, keep main weather
                            forecast = None

                    # === Feature 7: AIR QUALITY INDEX ===
                    if lat is not None and lon is not None:
                        try:
                            aqi_params = {
                                "lat": lat,
                                "lon": lon,
                                "appid": API_KEY
                            }
                            aqi_resp = requests.get(AQI_URL, params=aqi_params, timeout=5)
                            if aqi_resp.status_code == 200:
                                aqi_data = aqi_resp.json()
                                if aqi_data.get("list"):
                                    aqi_item = aqi_data["list"][0]
                                    aqi_value = aqi_item["main"]["aqi"]
                                    comps = aqi_item.get("components", {})
                                    aqi = {
                                        "index": aqi_value,
                                        "label": aqi_to_text(aqi_value),
                                        "pm2_5": comps.get("pm2_5"),
                                        "pm10": comps.get("pm10"),
                                    }
                        except requests.RequestException:
                            aqi = None

                else:
                    error = "❌ City not found or API issue. Check spelling or try another city."

            except requests.RequestException:
                error = "⚠️ Network error. Please check your internet connection."
        else:
            error = "Please enter a city name."

    return render_template(
        "index.html",
        weather=weather,
        error=error,
        city_query=city_query,
        forecast=forecast,
        aqi=aqi,
    )


if __name__ == "__main__":
    app.run(debug=True)
