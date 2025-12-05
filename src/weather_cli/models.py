from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WeatherData:
    id: Optional[int]
    city: str
    country: str
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int
    description: str
    wind_speed: float
    clouds: int
    timestamp: datetime
    forecast_time: datetime

    def __str__(self) -> str:
        return f"Weather in {self.city}, {self.country}: {self.temperature}°C, {self.description}"
