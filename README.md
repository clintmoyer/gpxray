# GPX Analyzer

A Python tool for validating GPX files and analyzing potential issues in GPS track data.

## Features

- Speed analysis using the haversine formula
- Elevation jump detection between consecutive points
- Track segment continuity validation
- Command-line interface for easy use

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the analyzer on a GPX file:

```bash
python gpx_analyzer.py analyze path/to/your/file.gpx
```

## Tests

Run the test suite:

```bash
pytest tests/
```

## License

MIT License 