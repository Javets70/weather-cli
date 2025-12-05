import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
# API Configuration
API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
BASE_URL: str = "https://api.openweathermap.org/data/2.5"
API_TIMEOUT: int = 10  # seconds

# Database Configuration
DB_URL = "./weather_data.db"
CACHE_DURATION: int = 1800  # 30 minutes in seconds

# API Endpoints (Limited to 4 as per requirement)
ENDPOINTS = {
    "current": f"{BASE_URL}/weather",
    "forecast": f"{BASE_URL}/forecast",
    "group": f"{BASE_URL}/group",
    "onecall": f"{BASE_URL}/onecall",
}
