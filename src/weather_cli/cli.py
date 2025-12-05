import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from requests.exceptions import Timeout, ConnectionError

from .api_client import WeatherAPIClient, APIError
from .database import Database
from .models import WeatherData

app = typer.Typer(
    name="weather-cli",
    help="Weather CLI - Fetch and manage weather data",
    add_completion=False,
)
console = Console()
db = Database()


def display_weather_table(weather_list: list[WeatherData]):
    """Display weather data in a formatted table."""
    if not weather_list:
        console.print("[yellow]No weather records found.[/yellow]")
        return

    table = Table(title="Weather Records", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("City", style="green")
    table.add_column("Country", style="blue", width=8)
    table.add_column("Temp (°C)", justify="right", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Humidity (%)", justify="right")
    table.add_column("Timestamp", style="dim")

    for weather in weather_list:
        table.add_row(
            str(weather.id),
            weather.city,
            weather.country,
            f"{weather.temperature:.1f}",
            weather.description.title(),
            f"{weather.humidity}",
            weather.timestamp.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def display_weather_detail(weather: WeatherData):
    """Display detailed weather information."""
    content = f"""
[bold cyan]Location:[/bold cyan] {weather.city}, {weather.country}
[bold yellow]Temperature:[/bold yellow] {weather.temperature:.1f}°C (Feels like {weather.feels_like:.1f}°C)
[bold blue]Range:[/bold blue] {weather.temp_min:.1f}°C - {weather.temp_max:.1f}°C
[bold green]Description:[/bold green] {weather.description.title()}
[bold magenta]Humidity:[/bold magenta] {weather.humidity}%
[bold white]Pressure:[/bold white] {weather.pressure} hPa
[bold cyan]Wind Speed:[/bold cyan] {weather.wind_speed} m/s
[bold yellow]Cloud Cover:[/bold yellow] {weather.clouds}%
[bold dim]Last Updated:[/bold dim] {weather.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
    """

    panel = Panel(
        content.strip(),
        title=f"[bold]Weather Details - ID: {weather.id}[/bold]",
        border_style="green",
    )
    console.print(panel)


def display_forecast_table(forecast_list: list[WeatherData]):
    """Display forecast data in a formatted table."""
    if not forecast_list:
        console.print("[yellow]No forecast records found.[/yellow]")
        return

    table = Table(title="Weather Forecast", show_header=True, header_style="bold magenta")
    table.add_column("Date/Time", style="cyan", width=16)
    table.add_column("Temp (°C)", justify="right", style="yellow")
    table.add_column("Feels Like", justify="right", style="yellow")
    table.add_column("Description", style="green")
    table.add_column("Rain %", justify="right", style="blue")
    table.add_column("Humidity", justify="right", style="magenta")
    table.add_column("Wind (m/s)", justify="right", style="white")

    for forecast in forecast_list:
        table.add_row(
            forecast.forecast_time.strftime("%m/%d %H:%M"),
            f"{forecast.temperature:.1f}",
            f"{forecast.feels_like:.1f}",
            forecast.description.title(),
            f"{forecast.humidity}%",
            f"{forecast.wind_speed:.1f}",
        )

    console.print(table)


def display_forecast_detail(forecast: WeatherData):
    """Display detailed forecast information."""
    content = f"""
[bold cyan]Location:[/bold cyan] {forecast.city}, {forecast.country}
[bold yellow]Forecast Time:[/bold yellow] {forecast.forecast_time.strftime("%Y-%m-%d %H:%M")}
[bold yellow]Temperature:[/bold yellow] {forecast.temperature:.1f}°C 
[bold blue]Range:[/bold blue] {forecast.temp_min:.1f}°C - {forecast.temp_max:.1f}°C
[bold green]Description:[/bold green] {forecast.description.title()}
[bold magenta]Humidity:[/bold magenta] {forecast.humidity}%
[bold white]Pressure:[/bold white] {forecast.pressure} hPa
[bold cyan]Wind Speed:[/bold cyan] {forecast.wind_speed} m/s
[bold yellow]Cloud Cover:[/bold yellow] {forecast.clouds}%
[bold dim]Fetched At:[/bold dim] {forecast.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
    """

    panel = Panel(
        content.strip(),
        title=f"[bold]Forecast Details - ID: {forecast.id}[/bold]",
        border_style="blue",
    )
    console.print(panel)


@app.command()
def fetch(
    city: str = typer.Argument(..., help="City name"),
    country: str | None = typer.Option(None, "--country", "-c", help="Country code (e.g., US, GB)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache and fetch fresh data"),
):
    """
    Fetch current weather for a city.

    Example:
        weather-cli fetch London --country GB
    """
    try:
        # Check cache first
        if not no_cache:
            cached = db.get_cached_weather(city, country)
            if cached:
                console.print("[green]✓[/green] Using cached data (less than 30 minutes old)")
                display_weather_detail(cached)
                return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description=f"Fetching weather for {city}...", total=None)

            client = WeatherAPIClient()
            weather = client.fetch_current_weather(city, country)

        weather.id = db.save_weather(weather)

        console.print("[green]✓[/green] Weather data fetched and saved successfully!")
        display_weather_detail(weather)

    except APIError as e:
        console.print(f"[red]✗ API Error:[/red] {str(e)}")
        raise typer.Exit(code=1)

    except Timeout:
        console.print("[red]✗ Request timed out.[/red] Please check your internet connection.")
        raise typer.Exit(code=1)

    except ConnectionError as e:
        console.print(f"[red]✗ Network Error:[/red] {str(e)}")
        raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]✗ Invalid Response:[/red] {str(e)}")
        raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]✗ Unexpected Error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def list(
    city: Optional[str] = typer.Option(None, "--city", "-c", help="Filter by city name"),
    country: Optional[str] = typer.Option(None, "--country", help="Filter by country code"),
    min_temp: Optional[float] = typer.Option(None, "--min-temp", help="Minimum temperature filter"),
    max_temp: Optional[float] = typer.Option(None, "--max-temp", help="Maximum temperature filter"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of records"),
):
    """
    List weather records with optional filtering.

    Example:
        weather-cli list --city London --min-temp 10
    """
    try:
        weather_list = db.list_weather(
            city=city,
            country=country,
            min_temp=min_temp,
            max_temp=max_temp,
            limit=limit,
        )

        display_weather_table(weather_list)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def show(record_id: int = typer.Argument(..., help="Weather record ID")):
    """
    Show detailed information for a specific weather record.

    Example:
        weather-cli show 1
    """
    try:
        weather = db.get_weather_by_id(record_id)

        if not weather:
            console.print(f"[yellow]No weather record found with ID: {record_id}[/yellow]")
            raise typer.Exit(code=1)

        display_weather_detail(weather)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def forecast(
    city: str = typer.Argument(..., help="City name"),
    country: str | None = typer.Option(None, "--country", "-c", help="Country code (e.g., US, GB)"),
    days: int = typer.Option(5, "--days", "-d", help="Number of days (1-5)"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save forecast to database"),
):
    """
    Fetch weather forecast for a city (3-hour intervals).

    Example:
        weather-cli forecast Tokyo --days 3
        weather-cli forecast "New York" --country US --days 5
    """
    try:
        # Validate days
        if not 1 <= days <= 5:
            console.print("[red]✗ Error:[/red] Days must be between 1 and 5")
            raise typer.Exit(code=1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description=f"Fetching {days}-day forecast for {city}...", total=None)

            client = WeatherAPIClient()
            forecasts = client.fetch_forecast(city, country, days)

        # Save to database if requested
        if save:
            for forecast_item in forecasts:
                forecast_item.id = db.save_weather(forecast_item)
            console.print(f"[green]✓[/green] {len(forecasts)} forecast records saved to database!")
        else:
            console.print(f"[green]✓[/green] Fetched {len(forecasts)} forecast records")

        # Display forecast table
        display_forecast_table(forecasts)

    except APIError as e:
        console.print(f"[red]✗ API Error:[/red] {str(e)}")
        raise typer.Exit(code=1)

    except Timeout:
        console.print("[red]✗ Request timed out.[/red] Please check your internet connection.")
        raise typer.Exit(code=1)

    except ConnectionError as e:
        console.print(f"[red]✗ Network Error:[/red] {str(e)}")
        raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]✗ Invalid Response:[/red] {str(e)}")
        raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]✗ Unexpected Error:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def info():
    """Display application information and usage statistics."""
    try:
        all_records = db.list_weather(limit=10000)

        if not all_records:
            console.print("[yellow]No weather records in database yet.[/yellow]")
            return

        total_records = len(all_records)
        cities = len(set(f"{w.city}, {w.country}" for w in all_records))
        avg_temp = sum(w.temperature for w in all_records) / total_records

        info_text = f"""
[bold cyan]Total Records:[/bold cyan] {total_records}
[bold green]Unique Cities:[/bold green] {cities}
[bold yellow]Average Temperature:[/bold yellow] {avg_temp:.1f}°C
[bold blue]Database Path:[/bold blue] {db.db_path}
[bold magenta]Cache Duration:[/bold magenta] 30 minutes
        """

        panel = Panel(
            info_text.strip(),
            title="[bold]Weather CLI Information[/bold]",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
