import os
import requests
from datetime import datetime


# ==========================================================
# CONFIGURATION
# ==========================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WEATHER_API_URL = (
    "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast"
)


# ==========================================================
# WEATHER EMOJIS
# ==========================================================

def get_weather_emoji(weather):
    weather_lower = weather.lower()

    if "thundery" in weather_lower:
        return "⛈️"

    elif "heavy rain" in weather_lower:
        return "🌧️"

    elif "moderate rain" in weather_lower:
        return "🌧️"

    elif "light rain" in weather_lower:
        return "🌦️"

    elif "showers" in weather_lower:
        return "🌦️"

    elif "cloudy" in weather_lower:
        return "☁️"

    elif "partly cloudy" in weather_lower:
        return "⛅"

    elif "fair" in weather_lower:
        return "☀️"

    elif "hazy" in weather_lower:
        return "🌫️"

    elif "windy" in weather_lower:
        return "💨"

    else:
        return "🌤️"


# ==========================================================
# GET WEATHER DATA FROM DATA.GOV.SG
# ==========================================================

def get_weather_data():

    print("Getting latest weather data from data.gov.sg...")

    response = requests.get(
        WEATHER_API_URL,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != 0:
        raise Exception(
            "data.gov.sg returned an error: "
            + str(data.get("errorMsg"))
        )

    items = data.get("data", {}).get("items", [])

    if not items:
        raise Exception(
            "No weather forecast was returned by data.gov.sg."
        )

    return items[0]


# ==========================================================
# GROUP AREAS BY WEATHER CONDITION
# ==========================================================

def group_forecasts(forecasts):

    grouped = {}

    for forecast in forecasts:

        area = forecast.get("area")
        weather = forecast.get("forecast")

        if not area or not weather:
            continue

        if weather not in grouped:
            grouped[weather] = []

        grouped[weather].append(area)

    return grouped


# ==========================================================
# FORMAT DATE / TIME
# ==========================================================

def format_update_time(timestamp):

    try:
        dt = datetime.fromisoformat(timestamp)

        return dt.strftime(
            "%d %b %Y, %I:%M %p"
        )

    except Exception:
        return timestamp


# ==========================================================
# CREATE TELEGRAM MESSAGE
# ==========================================================

def create_weather_message(weather_data):

    forecasts = weather_data.get("forecasts", [])

    valid_period = weather_data.get(
        "valid_period",
        {}
    )

    valid_period_text = valid_period.get(
        "text",
        "Not available"
    )

    update_timestamp = weather_data.get(
        "update_timestamp",
        ""
    )

    update_time = format_update_time(
        update_timestamp
    )

    grouped_forecasts = group_forecasts(
        forecasts
    )

    message = (
        "🌦️ SINGAPORE WEATHER UPDATE\n\n"
        f"🕐 Forecast Period: {valid_period_text}\n"
        f"🗓️ Updated: {update_time}\n\n"
    )

    for weather, areas in grouped_forecasts.items():

        emoji = get_weather_emoji(weather)

        message += (
            f"{emoji} {weather}\n"
        )

        area_text = ", ".join(areas)

        message += (
            f"📍 {area_text}\n\n"
        )

    message += (
        "Source: NEA / data.gov.sg 🇸🇬"
    )

    return message


# ==========================================================
# SEND MESSAGE TO TELEGRAM
# ==========================================================

def send_telegram_message(message):

    if not TELEGRAM_BOT_TOKEN:
        raise Exception(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    if not TELEGRAM_CHAT_ID:
        raise Exception(
            "TELEGRAM_CHAT_ID is missing."
        )

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    response = requests.post(
        telegram_url,
        data=payload,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise Exception(
            "Telegram API returned an error: "
            + str(result)
        )

    print("Telegram weather message sent successfully.")


# ==========================================================
# MAIN PROGRAM
# ==========================================================

def main():

    print("======================================")
    print("SG Weather Telegram Bot")
    print("======================================")

    try:

        # Step 1: Get latest weather data
        weather_data = get_weather_data()

        # Step 2: Format Telegram message
        message = create_weather_message(
            weather_data
        )

        # Step 3: Print message for GitHub Actions logs
        print()
        print(message)
        print()

        # Step 4: Send message to Telegram
        send_telegram_message(message)

        print()
        print("Weather bot completed successfully.")

    except Exception as error:

        print()
        print("ERROR:")
        print(error)

        raise


# ==========================================================
# RUN PROGRAM
# ==========================================================

if __name__ == "__main__":
    main()
