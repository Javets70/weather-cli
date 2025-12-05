import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .models import WeatherData
from .config import DB_URL, CACHE_DURATION


class Database:
    """SQLite database manager for weather data."""

    def __init__(self, db_path: Path = DB_URL):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    country TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    feels_like REAL NOT NULL,
                    temp_min REAL NOT NULL,
                    temp_max REAL NOT NULL,
                    pressure INTEGER NOT NULL,
                    humidity INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    wind_speed REAL NOT NULL,
                    clouds INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    UNIQUE(city, country)
                )
            """)

            # Create index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_city_country 
                ON weather(city, country)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON weather(timestamp)
            """)

    def save_weather(self, weather: WeatherData) -> int:
        """
        Save or update weather data in database.

        Args:
            weather: WeatherData object to save

        Returns:
            ID of the saved record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO weather (
                    city, country, temperature, feels_like, 
                    temp_min, temp_max, pressure, humidity,
                    description, wind_speed, clouds, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(city, country) DO UPDATE SET
                    temperature=excluded.temperature,
                    feels_like=excluded.feels_like,
                    temp_min=excluded.temp_min,
                    temp_max=excluded.temp_max,
                    pressure=excluded.pressure,
                    humidity=excluded.humidity,
                    description=excluded.description,
                    wind_speed=excluded.wind_speed,
                    clouds=excluded.clouds,
                    timestamp=excluded.timestamp
            """,
                (
                    weather.city,
                    weather.country,
                    weather.temperature,
                    weather.feels_like,
                    weather.temp_min,
                    weather.temp_max,
                    weather.pressure,
                    weather.humidity,
                    weather.description,
                    weather.wind_speed,
                    weather.clouds,
                    weather.timestamp,
                ),
            )
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else cursor.lastrowid

    def get_cached_weather(self, city: str, country: Optional[str] = None) -> Optional[WeatherData]:
        """
        Get cached weather data if it's still fresh.

        Args:
            city: City name
            country: Optional country code

        Returns:
            WeatherData if cache is fresh, None otherwise
        """
        cache_cutoff = datetime.now() - timedelta(seconds=CACHE_DURATION)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if country:
                cursor = conn.execute(
                    """
                    SELECT * FROM weather 
                    WHERE city like ? AND country = ? AND timestamp > ?
                """,
                    (city, country, cache_cutoff),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM weather 
                    WHERE city like ? AND timestamp > ?
                """,
                    (city, cache_cutoff),
                )

            row = cursor.fetchone()
            if row:
                return self._row_to_weather(row)

        return None

    def get_weather_by_id(self, record_id: int) -> Optional[WeatherData]:
        """
        Get weather record by ID.

        Args:
            record_id: Database record ID

        Returns:
            WeatherData if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM weather WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_weather(row)

        return None

    def list_weather(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        min_temp: Optional[float] = None,
        max_temp: Optional[float] = None,
        limit: int = 50,
    ) -> List[WeatherData]:
        """
        List weather records with optional filtering.

        Args:
            city: Filter by city name (partial match)
            country: Filter by country code
            min_temp: Filter by minimum temperature
            max_temp: Filter by maximum temperature
            limit: Maximum number of records to return

        Returns:
            List of WeatherData objects
        """
        query = "SELECT * FROM weather WHERE 1=1"
        params = []

        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")

        if country:
            query += " AND country = ?"
            params.append(country)

        if min_temp is not None:
            query += " AND temperature >= ?"
            params.append(min_temp)

        if max_temp is not None:
            query += " AND temperature <= ?"
            params.append(max_temp)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_weather(row) for row in cursor.fetchall()]

    def _row_to_weather(self, row: sqlite3.Row) -> WeatherData:
        """Convert database row to WeatherData object."""
        return WeatherData(
            id=row["id"],
            city=row["city"],
            country=row["country"],
            temperature=row["temperature"],
            feels_like=row["feels_like"],
            temp_min=row["temp_min"],
            temp_max=row["temp_max"],
            pressure=row["pressure"],
            humidity=row["humidity"],
            description=row["description"],
            wind_speed=row["wind_speed"],
            clouds=row["clouds"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
