from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

API_KEY = "5490d2b4b39c33a608fc3a3e931dbf5e"
CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AQI_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

def unix_to_time(unix_ts, offset_seconds):
    """Converts Unix timestamp to City's Local Time string."""
    # Convert to UTC, then apply the city's specific offset
    utc_time = datetime.utcfromtimestamp(unix_ts)
    local_time = utc_time + timedelta(seconds=offset_seconds)
    return local_time.strftime('%I:%M %p') # Format: 06:30 AM

def aqi_to_text(aqi_value: int) -> str:
    mapping = {1: "Good 😀", 2: "Fair 🙂", 3: "Moderate 😐", 4: "Poor 😷", 5: "Very Poor 🚫"}
    return mapping.get(aqi_value, "Unknown")

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
            params = {"q": city_query, "appid": API_KEY, "units": "metric"}

            try:
                resp = requests.get(CURRENT_URL, params=params, timeout=5)

                if resp.status_code == 200:
                    data = resp.json()
                    main = data["main"]
                    sys = data["sys"]
                    tz_shift = data.get("timezone", 0)

                    # Build weather dict with keys that match HTML exactly
                    weather = {
                        "city_name": f"{data['name']}, {sys.get('country', '')}",
                        "temperature": main["temp"],
                        "humidity": main["humidity"],
                        "pressure": main["pressure"],
                        "visibility": data.get("visibility", 0),
                        "description": data["weather"][0]["description"].capitalize(),
                        "wind_speed": data["wind"]["speed"],
                        "icon_url": f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",
                        "timezone_offset": tz_shift,
                        # Matches {{ weather.sunrise_time }} in HTML
                        "sunrise_time": unix_to_time(sys["sunrise"], tz_shift),
                        "sunset_time": unix_to_time(sys["sunset"], tz_shift),
                    }

                    # Coords for AQI and Forecast
                    lat, lon = data["coord"]["lat"], data["coord"]["lon"]

                    # AQI Call
                    aqi_resp = requests.get(AQI_URL, params={"lat": lat, "lon": lon, "appid": API_KEY})
                    if aqi_resp.status_code == 200:
                        aqi_val = aqi_resp.json()["list"][0]["main"]["aqi"]
                        aqi = {"index": aqi_val, "label": aqi_to_text(aqi_val)}

                    # Forecast Call
                    f_resp = requests.get(FORECAST_URL, params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"})
                    if f_resp.status_code == 200:
                        f_list = f_resp.json().get("list", [])
                        forecast = []
                        for i in range(0, min(len(f_list), 40), 8):
                            item = f_list[i]
                            date_obj = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
                            forecast.append({
                                "date": date_obj.strftime("%d %b"),
                                "temp": round(item["main"]["temp"]),
                                "description": item["weather"][0]["description"],
                                "icon": f"http://openweathermap.org/img/wn/{item['weather'][0]['icon']}@2x.png"
                            })
                else:
                    error = "❌ City not found."
            except Exception:
                error = "⚠️ Connection error."

    return render_template("index.html", weather=weather, error=error, city_query=city_query, forecast=forecast, aqi=aqi)

if __name__ == "__main__":
    app.run(debug=True)
