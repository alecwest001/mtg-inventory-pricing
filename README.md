# MTG Inventory & Pricing Prototype

A work-in-progress Magic: The Gathering inventory and pricing system built with Excel/VBA and Python.

This project was originally built as an assistive tool for a local game store (LGS) that was considering cataloguing its singles inventory. The store ultimately decided not to pursue cataloguing its singles, but the project became a useful way for me to expand my Python knowledge and apply it to a practical application.

I decided to continue developing it as a personal project, portfolio project, and potentially useful tool for others.

## What It Does

The project combines an Excel/VBA front end with a local Python HTTP server to manage card inventory and retrieve pricing information.

The current system can:

* Manually enter card inventory
* Search existing inventory
* Identify cards using card name, set, and card number
* Store quantity, condition, printing, and language
* Retrieve pricing from local MTGJSON data
* Retrieve live pricing from JustTCG
* Maintain local MTGJSON databases
* Check for updated MTGJSON data
* Run pricing functionality through a local Python server
* Keep the JustTCG API key outside of the Excel workbook

The Excel workbook is an integral part of the application rather than simply a demonstration interface. It contains the primary user interface and the VBA functionality that interacts with the Python backend.

## Architecture

```text
Excel / VBA
    |
    | HTTP requests
    v
Python HTTP Server
    |
    +---------------------+
    |                     |
    v                     v
MTGJSON                JustTCG
Local Card Data        Live Pricing
```

The separation between the Excel front end and Python backend allows the project to handle external API communication and local data processing outside of Excel.

## Technology

* Microsoft Excel
* VBA
* Python
* Python `http.server`
* REST APIs
* JSON
* MTGJSON
* JustTCG
* PyInstaller
* PowerShell
* Windows batch scripting

## Current Status

**Work in progress.**

The core application is functional, but several planned features are still under development.

### Working

**Inventory**

* Manual inventory entry
* Inventory search
* Card name, set, card number, quantity, condition, printing, and language fields

**Pricing**

* MTGJSON pricing
* JustTCG live pricing
* Separate workflows for local and live pricing

**MTGJSON**

* Local database files
* Database update utility
* Remote update detection
* Database replacement when updates are available

**Application**

* Excel/VBA front end
* Python local HTTP server
* API communication between Excel and Python
* Local configuration for API credentials
* Server health checking

### In Progress

**Card ID Matching**

The current pricing workflows can identify cards using search criteria, but the project is being upgraded to use card identifiers to improve reliability when matching cards between MTGJSON and JustTCG.

This is particularly useful because the two data sources do not always use identical naming conventions for sets and cards.

### Planned

**Inventory Import**

* CSV imports from multiple sources
* Additional methods for bulk inventory entry

**Card Entry Tool**

A dedicated card-entry sheet that can query the local database and allow cards to be selected based on search criteria rather than requiring all identifying information to be entered manually.

**Duplicate Consolidation**

A data-processing step that will combine duplicate cards entered into inventory into a single line item and update the quantity accordingly.

**Automated Database Updates**

The current MTGJSON updater is functional, but the planned application will periodically check for database updates while running.

The intended update-check interval is approximately four hours.

**Inventory Valuation**

A complete inventory valuation system using card quantities and current pricing data.

## MTGJSON

MTGJSON is used as a local source of structured Magic: The Gathering card data and pricing information.

The project stores the required MTGJSON databases locally rather than requiring the application to download the complete datasets during normal operation.

The `MTGJSONUpdater` utility checks the remote files for changes and updates the local databases when appropriate.

The current updater can determine whether the local files are current and download updated versions. Periodic background update checking is planned but has not yet been implemented.

## JustTCG

JustTCG is used for live card pricing.

The original implementation made API calls directly from Excel/Power Query while the API integration was being developed. Once the API implementation was working, the project was migrated to a Python backend.

The Python server now handles communication with JustTCG, keeping the API credentials and API-specific processing outside of the Excel workbook.

## Development Challenge

One of the most challenging parts of the project was getting the JustTCG API integration working correctly through Power Query in the original Excel implementation.

That initial implementation provided the foundation for understanding the API and its responses. The pricing functionality was later migrated into Python as the project evolved toward a client/server architecture.

Another ongoing challenge is reconciling card identifiers and naming conventions between MTGJSON and JustTCG. The project is being developed to use card IDs rather than relying exclusively on search terms.

## Project Structure

```text
Card Pricing Prototype/
├── .gitignore
├── config.ini.example
├── check_uuid.py
├── MTGJSONUpdater.spec
├── PriceServer.spec
├── price_server.py
├── start_server.bat
├── Store - Inventory Test v2.xlsm
└── update_mtgjson.py
```

Generated databases, compiled executables, debug files, test environments, and local configuration files are excluded from version control.

## Configuration

The Python server requires a JustTCG API key.

Create a copy of `config.ini.example` named:

```text
config.ini
```

Then add your API key:

```ini
[JustTCG]
api_key=YOUR_JUSTTCG_API_KEY
```

The actual `config.ini` file is intentionally excluded from Git.

## Running the Project

The intended Windows workflow is:

```text
start_server.bat
       |
       v
MTGJSON database check
       |
       v
Python HTTP server
       |
       v
Excel inventory workbook
```

The launcher checks the local MTGJSON databases before starting the price server. It then waits for the Python server to report that it is ready before opening the Excel workbook.

## Why I Built It

I originally built this project to create something useful for an LGS while expanding my knowledge of Python and API development.

The project evolved beyond its original purpose into a practical exercise in connecting several different technologies into a working application.

More than anything, I'm proud that it became a working product rather than remaining a collection of experiments.

I continue to develop it in my spare time as a way to learn, experiment, and potentially build something that other people may find useful.

## Future Development

The project will continue to evolve as new ideas and requirements are explored.

Some of the planned development includes:

* Card ID-based matching
* CSV inventory imports
* Database-assisted card entry
* Duplicate inventory consolidation
* Four-hour MTGJSON update checks
* Automatic database updates
* Full inventory valuation
* Additional inventory management functionality
* Further improvements to the Excel interface

## Author

Alec West

## Disclaimer

This is an independent personal project and is not affiliated with MTGJSON or JustTCG.

Pricing and card data are provided by external services and may change independently of this project.
