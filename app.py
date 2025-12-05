from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)

API_KEY = "5490d2b4b39c33a608fc3a3e931dbf5e"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def unix_to_time(unix_ts):
    """Convert Unix timestamp to HH:MM:SS (24-hr)."""
    return datetime.fromtimestamp(unix_ts).strftime('%H:%M:%S')


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None
    city_query = ""

    if request.method == "POST":
        city_query = request.form.get("city", "").strip()

        if city_query:
            params = {
                "q": city_query,
                "appid": API_KEY,
                "units": "metric"
            }

            try:
                resp = requests.get(BASE_URL, params=params, timeout=5)

                if resp.status_code == 200:
                    data = resp.json()

                    main = data["main"]
                    weather_info = data["weather"][0]
                    wind = data["wind"]
                    sys = data["sys"]

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
                    }
                else:
                    error = "❌ City not found or API issue. Check spelling or try another city."
            except requests.RequestException:
                error = "⚠️ Network error. Please check your internet connection."
        else:
            error = "Please enter a city name."

    return render_template("index.html", weather=weather, error=error, city_query=city_query)


if __name__ == "__main__":
    app.run(debug=True)
