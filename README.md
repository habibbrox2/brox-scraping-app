# ScrapMaster Desktop

A production-ready desktop web scraping application with modern GUI, built using Python 3.12+, CustomTkinter, and Playwright.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### Core Features
- **Modern Dashboard UI** - Beautiful sidebar navigation with dark/light mode
- **Job Creator** - Visual builder with CSS/XPath selector support
- **Job Management** - Run, edit, delete, and duplicate jobs with real-time status
- **Results Viewer** - Data table with search, filter, sort, and export to CSV/Excel/JSON
- **Built-in Templates** - Ready-to-use templates for Amazon, BooksToScrape, Google Shopping, etc.
- **Settings** - Configurable browser, storage, and logging options

### Technical Features
- **Playwright + BeautifulSoup** - Dual scraping engine with fallback
- **SQLite Database** - Local data storage with optional MongoDB export
- **Threading + APScheduler** - Concurrent job execution and scheduling
- **Logging** - Full logging with loguru
- **Export Formats** - CSV, Excel, JSON

## Installation

### Prerequisites
- Python 3.12+
- pip

### Install Dependencies

```bash
# Clone the repository
cd ScrapMaster-Desktop

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Running the Application

```bash
python main.py
```

## Building the Executable

### Windows (PyInstaller)

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller build.spec --clean

# Executable will be in dist/
```

### macOS

```bash
# Install PyInstaller
pip install pyinstaller

# Build (using spec file)
pyinstaller build.spec --clean

# .app will be in dist/
```

### Linux

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller main.py --onefile --windowed

# Executable will be in dist/
```

## Project Structure

```
ScrapMaster-Desktop/
├── main.py                 # Application entry point
├── app/
│   ├── __init__.py       # App initialization
│   ├── gui/              # GUI components
│   │   ├── main_window.py
│   │   ├── dashboard.py
│   │   ├── job_form.py
│   │   ├── job_list.py
│   │   ├── results.py
│   │   ├── templates.py
│   │   └── settings.py
│   ├── scraper/         # Scraping engine
│   │   ├── playwright_service.py
│   │   └── scraper_engine.py
│   ├── database/         # Database handling
│   │   ├── models.py
│   │   └── db.py
│   └── utils/           # Utilities
│       ├── logger.py
│       └── helpers.py
├── requirements.txt     # Dependencies
├── build.spec         # PyInstaller spec
└── README.md         # Documentation
```

## Usage

### Creating a Job

1. Click "New Job" in the sidebar
2. Enter the target URL
3. Define data fields using CSS/XPath selectors
4. Configure browser settings (headless mode, delay, etc.)
5. Optionally enable pagination
6. Save the job

### Running a Job

1. Go to "My Jobs"
2. Click "Run" on the desired job
3. View progress in real-time
4. Check results in "Results"

### Exporting Data

1. Go to "Results"
2. Filter by job or search
3. Click export button (CSV, Excel, or JSON)

## Built-in Templates

| Template | Description |
|----------|-------------|
| Amazon Product Scraper | Scrape product listings from Amazon |
| BooksToScrape Demo | Demo scraper for testing |
| Google Shopping | Scrape Google Shopping results |
| News Article | Generic news article scraper |
| E-commerce General | Generic e-commerce scraper |
| LinkedIn Profile | Public LinkedIn profile scraper |

## Configuration

### Settings Options

- **Max Concurrent Jobs**: Number of jobs to run simultaneously
- **Default Headless Mode**: Run browser without UI
- **Default Delay**: Delay between requests (ms)
- **Data Storage Path**: Where to store scraped data
- **Dark Mode**: Toggle dark/light theme

### Browser Options

- Headless mode
- Custom User-Agent
- Proxy support
- Viewport size
- Stealth mode

## Troubleshooting

### Playwright Not Found

```bash
playwright install chromium
```

### Database Error

Ensure the data directory has write permissions.

### Export Error

Install required packages:
```bash
pip install pandas openpyxl
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please submit a pull request.

---

**ScrapMaster Desktop** - Modern Web Scraping Made Easy