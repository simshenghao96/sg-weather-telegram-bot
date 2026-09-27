import os
import math
import requests
from datetime import datetime


# ==========================================================
# CONFIGURATION
# ==========================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TWO_HOUR_FORECAST_URL = (
    "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast"
)

RAINFALL_URL = (
    "https://api-open.data.gov.sg/v2/real-time/api/rainfall"
)

TEMPERATURE_URL = (
    "https://api-open.data.gov.sg/v2/real-time/api/air-temperature"
)


# ==========================================================
# REGIONAL REFERENCE POINTS
# ==========================================================
#
# Used to group stations and forecast areas into:
# North / East / South / West / Central
#
# These are approximate groupings for easier reading.
# They are NOT official NEA administrative boundaries.
#
# ==========================================================

REGION_CENTRES = {
    "North": {
        "latitude": 1.418,
        "longitude": 103.820
    },

    "East": {
        "latitude": 1.357,
        "longitude": 103.940
    },

    "South": {
        "latitude": 1.270,
        "longitude": 103.820
    },

    "West": {
        "latitude": 1.357,
        "longitude": 103.700
    },

    "Central": {
        "latitude": 1.350,
        "longitude": 103.820
    }
}


REGION_EMOJIS = {
    "North": "⬆️",
    "East": "➡️",
    "South": "⬇️",
    "West": "⬅️",
    "Central": "🔘"
}


REGION_ORDER = [
    "North",
    "East",
    "South",
    "West",
    "Central"
]


# ==========================================================
# DETERMINE REGION FROM COORDINATES
# ==========================================================

def get_region(latitude, longitude):

    closest_region = None
    closest_distance = float("inf")

    for region, coordinates in REGION_CENTRES.items():

        region_lat = coordinates["latitude"]
        region_lon = coordinates["longitude"]

        lat_difference = latitude - region_lat

        lon_difference = (
            longitude - region_lon
        ) * math.cos(
            math.radians(latitude)
        )

        distance = (
            lat_difference ** 2
            + lon_difference ** 2
        )

        if distance < closest_distance:

            closest_distance = distance
            closest_region = region

    return closest_region


# ==========================================================
# WEATHER EMOJI
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
# FORMAT TIMESTAMP
# ==========================================================

def format_timestamp(timestamp):

    if not timestamp:
        return "Not available"

    try:

        dt = datetime.fromisoformat(timestamp)

        return dt.strftime(
            "%d %b %Y, %I:%M %p"
        )

    except Exception:

        return timestamp


# ==========================================================
# CALL DATA.GOV.SG API
# ==========================================================

def get_api_data(url, description):

    print(
        f"Getting {description} from data.gov.sg..."
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if result.get("code") != 0:

        raise Exception(
            f"{description} API error: "
            + str(result.get("errorMsg"))
        )

    return result.get("data", {})


# ==========================================================
# GET 2-HOUR FORECAST
# ==========================================================

def get_forecast_data():

    return get_api_data(
        TWO_HOUR_FORECAST_URL,
        "2-hour forecast"
    )


# ==========================================================
# GET RAINFALL DATA
# ==========================================================

def get_rainfall_data():

    return get_api_data(
        RAINFALL_URL,
        "rainfall readings"
    )


# ==========================================================
# GET TEMPERATURE DATA
# ==========================================================

def get_temperature_data():

    return get_api_data(
        TEMPERATURE_URL,
        "temperature readings"
    )


# ==========================================================
# CREATE STATION LOOKUP
# ==========================================================

def create_station_lookup(stations):

    lookup = {}

    for station in stations:

        station_id = station.get("id")

        location = station.get(
            "location",
            {}
        )

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if (
            station_id
            and latitude is not None
            and longitude is not None
        ):

            lookup[station_id] = {
                "name": station.get(
                    "name",
                    station_id
                ),

                "latitude": latitude,
                "longitude": longitude,

                "region": get_region(
                    latitude,
                    longitude
                )
            }

    return lookup


# ==========================================================
# CURRENT RAINFALL STATUS
# ==========================================================

def create_rainfall_section(data):

    stations = data.get(
        "stations",
        []
    )

    readings = data.get(
        "readings",
        []
    )

    if not readings:

        return (
            "🌧️ CURRENT RAINFALL STATUS\n"
            "Latest rainfall measurements from weather stations\n\n"
            "Rainfall data is currently unavailable.\n"
        )

    station_lookup = create_station_lookup(
        stations
    )

    latest = readings[0]

    timestamp = latest.get(
        "timestamp",
        ""
    )

    reading_data = latest.get(
        "data",
        []
    )

    regions = {
        region: []
        for region in REGION_ORDER
    }

    for reading in reading_data:

        station_id = reading.get(
            "stationId"
        )

        value = reading.get(
            "value",
            0
        )

        station = station_lookup.get(
            station_id
        )

        if not station:
            continue

        # Only show stations where rainfall
        # was measured in the latest reading.
        if value is not None and value > 0:

            region = station["region"]

            regions[region].append({
                "name": station["name"],
                "rainfall": value
            })

    message = (
        "🌧️ CURRENT RAINFALL STATUS\n"
        "Latest rainfall measurements from weather stations\n"
        f"🕐 Latest 5-min reading: "
        f"{format_timestamp(timestamp)}\n\n"
    )

    rain_found = False

    for region in REGION_ORDER:

        stations_in_region = regions[
            region
        ]

        if not stations_in_region:
            continue

        rain_found = True

        message += (
            f"{REGION_EMOJIS[region]} "
            f"{region}\n"
        )

        stations_in_region.sort(
            key=lambda item:
            item["rainfall"],
            reverse=True
        )

        for station in stations_in_region:

            message += (
                f"• {station['name']}: "
                f"{station['rainfall']:.1f} mm\n"
            )

        message += "\n"

    if not rain_found:

        message += (
            "✅ No rainfall was measured at the "
            "reporting weather stations during "
            "the latest 5-minute reading.\n\n"
        )

    return message


# ==========================================================
# CURRENT TEMPERATURE
# ==========================================================

def create_temperature_section(data):

    stations = data.get(
        "stations",
        []
    )

    readings = data.get(
        "readings",
        []
    )

    if not readings:

        return (
            "🌡️ CURRENT TEMPERATURE\n\n"
            "Temperature data is currently unavailable.\n"
        )

    station_lookup = create_station_lookup(
        stations
    )

    latest = readings[0]

    timestamp = latest.get(
        "timestamp",
        ""
    )

    reading_data = latest.get(
        "data",
        []
    )

    regions = {
        region: []
        for region in REGION_ORDER
    }

    all_temperatures = []

    for reading in reading_data:

        station_id = reading.get(
            "stationId"
        )

        value = reading.get(
            "value"
        )

        station = station_lookup.get(
            station_id
        )

        if (
            not station
            or value is None
        ):
            continue

        region = station["region"]

        regions[region].append({
            "name": station["name"],
            "temperature": value
        })

        all_temperatures.append(
            value
        )

    message = (
        "🌡️ CURRENT TEMPERATURE\n"
        "Actual readings from weather stations\n"
        f"🕐 Latest reading: "
        f"{format_timestamp(timestamp)}\n\n"
    )

    if all_temperatures:

        overall_low = min(
            all_temperatures
        )

        overall_high = max(
            all_temperatures
        )

        overall_average = (
            sum(all_temperatures)
            / len(all_temperatures)
        )

        message += (
            "🇸🇬 Singapore Overall\n"
            f"• Lowest: {overall_low:.1f}°C\n"
            f"• Highest: {overall_high:.1f}°C\n"
            f"• Average: {overall_average:.1f}°C\n\n"
        )

    for region in REGION_ORDER:

        region_readings = regions[
            region
        ]

        if not region_readings:
            continue

        temperatures = [
            item["temperature"]
            for item in region_readings
        ]

        lowest = min(
            temperatures
        )

        highest = max(
            temperatures
        )

        average = (
            sum(temperatures)
            / len(temperatures)
        )

        message += (
            f"{REGION_EMOJIS[region]} "
            f"{region}\n"
        )

        message += (
            f"• Average: "
            f"{average:.1f}°C\n"
        )

        message += (
            f"• Range: "
            f"{lowest:.1f}°C – "
            f"{highest:.1f}°C\n"
        )

        for station in region_readings:

            message += (
                f"  ↳ {station['name']}: "
                f"{station['temperature']:.1f}°C\n"
            )

        message += "\n"

    return message


# ==========================================================
# NEXT 2 HOURS FORECAST
# ==========================================================

def create_forecast_section(data):

    items = data.get(
        "items",
        []
    )

    area_metadata = data.get(
        "area_metadata",
        []
    )

    if not items:

        return (
            "🌦️ NEXT 2 HOURS — FORECAST\n"
            "Expected weather conditions\n\n"
            "Forecast currently unavailable.\n"
        )

    latest = items[0]

    forecasts = latest.get(
        "forecasts",
        []
    )

    valid_period = latest.get(
        "valid_period",
        {}
    )

    update_timestamp = latest.get(
        "update_timestamp",
        ""
    )

    area_coordinates = {}

    for area in area_metadata:

        location = area.get(
            "label_location",
            {}
        )

        latitude = location.get(
            "latitude"
        )

        longitude = location.get(
            "longitude"
        )

        if (
            latitude is not None
            and longitude is not None
        ):

            area_coordinates[
                area.get("name")
            ] = (
                latitude,
                longitude
            )

    regions = {
        region: {}
        for region in REGION_ORDER
    }

    for forecast in forecasts:

        area_name = forecast.get(
            "area"
        )

        condition = forecast.get(
            "forecast"
        )

        coordinates = area_coordinates.get(
            area_name
        )

        if (
            not area_name
            or not condition
            or not coordinates
        ):
            continue

        latitude, longitude = coordinates

        region = get_region(
            latitude,
            longitude
        )

        if condition not in regions[region]:

            regions[region][condition] = []

        regions[region][condition].append(
            area_name
        )

    message = (
        "🌦️ NEXT 2 HOURS — FORECAST\n"
        "Expected weather conditions — "
        "not necessarily happening right now\n"
        f"🕐 Forecast period: "
        f"{valid_period.get('text', 'Not available')}\n"
        f"🗓️ Forecast updated: "
        f"{format_timestamp(update_timestamp)}\n\n"
    )

    for region in REGION_ORDER:

        region_forecasts = regions[
            region
        ]

        if not region_forecasts:
            continue

        message += (
            f"{REGION_EMOJIS[region]} "
            f"{region}\n"
        )

        for condition, areas in (
            region_forecasts.items()
        ):

            emoji = get_weather_emoji(
                condition
            )

            message += (
                f"{emoji} Expected: {condition}\n"
            )

            message += (
                "📍 "
                + ", ".join(areas)
                + "\n"
            )

        message += "\n"

    return message


# ==========================================================
# SPLIT LONG TELEGRAM MESSAGES
# ==========================================================

def split_message(
    message,
    max_length=3900
):

    if len(message) <= max_length:

        return [message]

    chunks = []

    current_chunk = ""

    for line in message.split("\n"):

        new_line = line + "\n"

        if (
            len(current_chunk)
            + len(new_line)
            > max_length
        ):

            chunks.append(
                current_chunk.rstrip()
            )

            current_chunk = ""

        current_chunk += new_line

    if current_chunk:

        chunks.append(
            current_chunk.rstrip()
        )

    return chunks


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
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/"
        "sendMessage"
    )

    chunks = split_message(
        message
    )

    for chunk in chunks:

        payload = {
            "chat_id":
                TELEGRAM_CHAT_ID,

            "text":
                chunk
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
                "Telegram API error: "
                + str(result)
            )

    print(
        "Telegram weather message "
        "sent successfully."
    )


# ==========================================================
# MAIN PROGRAM
# ==========================================================

def main():

    print(
        "======================================"
    )

    print(
        "SG Weather Telegram Bot"
    )

    print(
        "======================================"
    )

    try:

        # ==========================================
        # GET WEATHER DATA
        # ==========================================

        rainfall_data = (
            get_rainfall_data()
        )

        temperature_data = (
            get_temperature_data()
        )

        forecast_data = (
            get_forecast_data()
        )


        # ==========================================
        # CREATE MESSAGE SECTIONS
        # ==========================================

        rainfall_section = (
            create_rainfall_section(
                rainfall_data
            )
        )

        temperature_section = (
            create_temperature_section(
                temperature_data
            )
        )

        forecast_section = (
            create_forecast_section(
                forecast_data
            )
        )


        # ==========================================
        # BUILD FINAL MESSAGE
        # ==========================================

        message = (
            "🇸🇬 SINGAPORE WEATHER UPDATE\n\n"

            + rainfall_section
            + "\n"

            + temperature_section
            + "\n"

            + forecast_section
            + "\n"

            + "Source: NEA / data.gov.sg 🇸🇬\n"
            + "Regional grouping is approximate "
              "for easier reading."
        )


        # ==========================================
        # PRINT MESSAGE IN GITHUB ACTIONS LOG
        # ==========================================

        print()
        print(message)
        print()


        # ==========================================
        # SEND MESSAGE TO TELEGRAM
        # ==========================================

        send_telegram_message(
            message
        )

        print()

        print(
            "Weather bot completed successfully."
        )


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
