from datetime import datetime
from typing import Dict

import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

from .config import API_KEY, ENDPOINTS, API_TIMEOUT
from .models import WeatherData


class APIError(Exception):
    """Custom exception for API-related errors."""

    pass


class WeatherAPIClient:
    def __init__(self, api_key: str | None = None):
        """
        Args:
            api_key: OpenWeather API key. If None, uses API_KEY

        Raises:
            APIError: If no API key is provided
        """
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise APIError("No API key provided. Set OPENWEATHER_API_KEY environment variable.")

    def fetch_current_weather(self, city: str, country_code: str | None = None) -> WeatherData:
        """
        Fetch current weather data for a city.

        Args:
            city: City name
            country_code: Optional ISO 3166 country code (e.g., 'US', 'GB')

        Returns:
            WeatherData object with current weather information

        Raises:
            APIError: If API request fails
            ValueError: If response data is invalid or malformed
            Timeout: If request times out
            ConnectionError: If network connection fails
        """
        location = f"{city},{country_code}" if country_code else city

        params = {
            "q": location,
            "appid": self.api_key,
            "units": "metric",  # Celsius
        }

        try:
            response = requests.get(ENDPOINTS["current"], params=params, timeout=API_TIMEOUT)
            response.raise_for_status()

        except Timeout:
            raise Timeout(
                f"Request timed out after {API_TIMEOUT} seconds. "
                "Please check your internet connection and try again."
            )

        except ConnectionError as e:
            raise ConnectionError(
                f"Network connection failed: {str(e)}. Please check your internet connection."
            )

        except HTTPError as e:
            if response.status_code == 404:
                raise APIError(f"City '{location}' not found.")
            elif response.status_code == 401:
                raise APIError("Invalid API key. Please check your configuration.")
            elif response.status_code == 429:
                raise APIError("API rate limit exceeded. Please try again later.")
            else:
                raise APIError(f"HTTP error {response.status_code}: {str(e)}")

        except RequestException as e:
            raise APIError(f"Request failed: {str(e)}")

        try:
            data = response.json()
            return self._parse_weather_data(data)

        except ValueError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except KeyError as e:
            raise ValueError(f"Missing required field in response: {str(e)}")

    def _parse_weather_data(self, data: Dict) -> WeatherData:
        """
        Parse API response into WeatherData model.

        Args:
            data: Raw API response dictionary

        Returns:
            WeatherData object

        Raises:
            ValueError: If required fields are missing or malformed
        """
        try:
            # Validate required fields exist
            required_fields = ["name", "sys", "main", "weather", "wind", "clouds"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Extract nested data with validation
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]
            wind = data.get("wind", {})
            sys = data.get("sys", {})
            clouds = data.get("clouds", {})

            # Validate required nested fields
            if not weather:
                raise ValueError("No weather description available")

            return WeatherData(
                id=None,  # Will be set by database
                city=data["name"],
                country=sys.get("country", "Unknown"),
                temperature=float(main.get("temp", 0)),
                feels_like=float(main.get("feels_like", 0)),
                temp_min=float(main.get("temp_min", 0)),
                temp_max=float(main.get("temp_max", 0)),
                pressure=int(main.get("pressure", 0)),
                humidity=int(main.get("humidity", 0)),
                description=weather.get("description", "No description"),
                wind_speed=float(wind.get("speed", 0)),
                clouds=int(clouds.get("all", 0)),
                timestamp=datetime.now(),
            )

        except (KeyError, ValueError, TypeError, IndexError) as e:
            raise ValueError(f"Malformed response data: {str(e)}")
