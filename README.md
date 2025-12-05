# Weather CLI Application
A command line application to fetch weather data from OpenWeather API.

## Prerequisites

- Python 3.8 or higher
- OpenWeather API key (free tier available at https://openweathermap.org/api)

## Installation
## Optiona 1: uv
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package directly (will handle everything)
uv tool install --from git+https://github.com/yourusername/weather-cli.git weather-cli

# Or if you have the source locally:
cd weather-cli
uv tool install .

# Now use it anywhere:
weather fetch London
```

### Option 2: Traditional Installation

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
uv pip install -e .

# Now use it:
weather fetch London
```
