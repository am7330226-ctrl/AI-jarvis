"""
Web Search & Information Tool
==============================
Provides web searching, weather, and simple web-fetch capabilities.
All web interactions open in the system browser to keep Jarvis lightweight.
"""

import logging
import urllib.parse
import webbrowser
import requests

logger = logging.getLogger(__name__)

# wttr.in provides free, no-auth weather data in JSON format
WEATHER_API = "https://wttr.in/{city}?format=j1"
WEATHER_SIMPLE_API = "https://wttr.in/{city}?format=3"  # Returns: "City: ⛅ +25°C"


def search_web(query: str, engine: str = "duckduckgo") -> str:
    """
    Open a web search in the default browser.
    
    Args:
        query: The search query.
        engine: Search engine ('duckduckgo', 'google', 'bing').
    
    Returns:
        Status message.
    """
    encoded = urllib.parse.quote_plus(query)
    
    urls = {
        "duckduckgo": f"https://duckduckgo.com/?q={encoded}",
        "google": f"https://www.google.com/search?q={encoded}",
        "bing": f"https://www.bing.com/search?q={encoded}",
        "youtube": f"https://www.youtube.com/results?search_query={encoded}",
    }
    
    url = urls.get(engine.lower(), urls["duckduckgo"])
    logger.info(f"Opening web search: {query!r} on {engine}")
    webbrowser.open(url)
    return f"Searching for '{query}' on {engine.title()}."


def get_weather(city: str) -> str:
    """
    Fetch current weather for a city using wttr.in (no API key needed).
    
    Args:
        city: City name (e.g., 'London', 'New York').
    
    Returns:
        Weather summary string.
    """
    city_encoded = urllib.parse.quote_plus(city)
    url = WEATHER_SIMPLE_API.format(city=city_encoded)
    
    logger.info(f"Fetching weather for: {city!r}")
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        # Response is like: "Mumbai: ⛅ +30°C"
        weather_text = response.text.strip()
        logger.info(f"Weather response: {weather_text}")
        return weather_text
    except requests.exceptions.ConnectionError:
        return "I'm unable to reach the weather service. Please check your internet connection."
    except requests.exceptions.Timeout:
        return "The weather request timed out. Please try again."
    except Exception as e:
        logger.error(f"Weather fetch error: {e}")
        return f"Could not retrieve weather for {city}."


def get_weather_detailed(city: str) -> dict:
    """
    Fetch detailed weather data as a dict.
    
    Returns:
        Dict with keys: temperature, feels_like, humidity, description, wind_speed.
    """
    city_encoded = urllib.parse.quote_plus(city)
    url = WEATHER_API.format(city=city_encoded)
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        current = data["current_condition"][0]
        return {
            "temperature": f"{current['temp_C']}°C / {current['temp_F']}°F",
            "feels_like": f"{current['FeelsLikeC']}°C",
            "humidity": f"{current['humidity']}%",
            "description": current["weatherDesc"][0]["value"],
            "wind_speed": f"{current['windspeedKmph']} km/h",
            "city": city,
        }
    except Exception as e:
        logger.error(f"Detailed weather error: {e}")
        return {}


def open_url(url: str) -> str:
    """
    Open a specific URL in the default browser.
    
    Args:
        url: The URL to open.
    
    Returns:
        Status message.
    """
    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    logger.info(f"Opening URL: {url!r}")
    webbrowser.open(url)
    return f"Opened {url} in your browser."


def get_time_and_date() -> str:
    """Get the current time and date."""
    from datetime import datetime
    now = datetime.now()
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y.")
