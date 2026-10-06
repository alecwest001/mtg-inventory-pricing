# MTG Inventory & Pricing Prototype

A work-in-progress Magic: The Gathering inventory and pricing system built with Excel/VBA and Python.

This project was originally built as an assistive tool for a local game store (LGS) that was considering cataloguing its singles inventory. The store ultimately decided not to pursue cataloguing its singles, but the project became a useful way for me to expand my Python knowledge and apply it to a practical application.

I decided to continue developing it as a personal project, portfolio project, and potentially useful tool for others.

## What It Does

The project combines an Excel/VBA front end with a local Python HTTP server to manage card inventory and retrieve pricing information.

The current system can:

* Manually enter and search card inventory
* Identify cards using card name, set, and card number
* Store quantity, condition, printing, and language
* Retrieve cached pricing from local MTGJSON data
* Retrieve live pricing from JustTCG
* Match cards between MTGJSON and JustTCG using TCGplayer Product IDs
* Return pricing, card identity, and verification information to Excel
* Maintain and update local MTGJSON databases
* Monitor MTGJSON for database updates
* Notify the user when an update is available
* Update the databases from a Windows notification
* Restart the local Price Server after a successful update
* Verify the Price Server is healthy after an update
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
    +-----------------------------+
    |                             |
    v                             v
MTGJSON                       JustTCG
Local Card Data               Live Pricing
    |                             |
    | TCGplayer Product ID        |
    +---------------------------->|
                                  |
                                  v
                            ID Verification


MTGJSON Monitor
    |
    | Periodic update checks
    v
MTGJSON SHA-256 Verification
    |
    | Update available
    v
Windows Toast Notification
    |
    | Update Now
    v
MTGJSON Updater
    |
    | Successful database update
    v
Price Server Restart
    |
    v
Health Check
```

The Excel front end handles inventory management and user interaction while the Python backend handles local database access, API communication, cross-source card verification, and database maintenance.

The MTGJSON Monitor runs separately from the Price Server and coordinates database update detection, notifications, updates, and server restarts.

During development, `start_server.bat` acts as a multi-launch development entry point. It allows the application to be started using either the Python source files or compiled executables.

## Card Identification & Verification

A major part of the project is making sure that a live price returned by JustTCG actually corresponds to the card being requested.

The system uses MTGJSON as the initial source of card identity information. When a card is found, the system retrieves its MTGJSON UUID and TCGplayer Product ID.

The TCGplayer Product ID is then used to request the corresponding live pricing information from JustTCG.

The Python backend verifies that the TCGplayer Product ID returned by JustTCG matches the Product ID obtained from MTGJSON before marking the result as verified.

The system also returns additional information for auditing:

* MTGJSON UUID
* TCGplayer Product ID
* JustTCG card name
* JustTCG set
* Card number
* Condition
* Printing
* Language
* Verification status

This approach avoids relying exclusively on human-readable card names, which can differ between data sources. For example, the same product may appear as `Sol Ring` in the inventory while JustTCG identifies it as `Sol Ring (Borderless)`.

## MTGJSON Data Loading & Performance

The Price Server previously loaded the MTGJSON databases using Python's standard `json.load()` function. Because `AllPrintings.json.gz` contains a large amount of card data, loading the complete JSON document into memory created significant memory overhead during startup.

The Price Server has since been changed to use streaming JSON parsing through the Python `ijson` library.

Instead of constructing the complete JSON document in memory, the server processes the MTGJSON data incrementally and retains only the information required by the application.

For `AllPrintings.json.gz`, the server extracts:

* Card name
* Card number
* MTGJSON UUID
* TCGplayer Product ID
* Set code

Set codes are resolved to their human-readable MTGJSON set names and used to construct the card lookup index.

For `AllPricesToday.json.gz`, the server extracts the current MTGJSON paper TCGplayer retail prices for:

* Normal cards
* Foil cards
* Price date

Only the pricing data required by the application is retained.

This change substantially reduced the Price Server's memory usage during startup. During development testing, the previous implementation used roughly 1.8 GB of process memory while loading the databases, while the streaming implementation reduced the running server to well under 200 MB.

The streaming implementation was tested against multiple cards and sets, including Commander Masters, Prophecy, and Wilds of Eldraine: Enchanting Tales.

The Excel → PriceServer → MTGJSON pricing workflow was also tested with both existing and newly added inventory entries, including normal and foil pricing.

## MTGJSON Database Updates

MTGJSON is maintained locally so the application does not need to download the complete card and pricing datasets during normal operation.

The update system uses the SHA-256 values published by MTGJSON to determine whether the local databases are current.

When an update is detected, the updater:

1. Retrieves the published SHA-256 value.
2. Compares it with the local database.
3. Downloads the updated file to a temporary location.
4. Validates the downloaded gzip file.
5. Calculates and verifies the downloaded file's SHA-256.
6. Replaces the existing database only after validation succeeds.
7. Writes an update result describing what happened.

If an update fails validation, the existing database is retained.

The databases currently monitored are:

* `AllPricesToday.json.gz`
* `AllPrintings.json.gz`

## MTGJSON Monitor

The project includes a background MTGJSON monitoring process.

`mtgjson_monitor.py` periodically checks MTGJSON for updated database files. When an update is detected, the monitor displays a Windows toast notification with two options:

* **Update Now** starts the MTGJSON updater.
* **Later** dismisses the update without changing the local databases.

The **Update Now** action uses a registered Windows URI protocol:

```text
mtgjson-monitor://update
```

The monitor validates the URI before performing the requested action.

After the updater completes, the monitor reads the updater result and only restarts the Price Server when the MTGJSON databases were successfully updated.

The restart process is:

```text
MTGJSON update
      |
      v
Updater reports UPDATED
      |
      v
PriceServer shutdown
      |
      v
PriceServer restart
      |
      v
/health check
      |
      v
PriceServer ready
```

The monitor waits for the Price Server health endpoint to respond successfully before reporting that the restart has completed.

### Current Test Phase

The MTGJSON Monitor is currently being tested using a short check interval and forced update detection so that the complete workflow can be repeatedly tested without waiting for an actual MTGJSON release.

The current test interval is approximately:

```text
30 seconds
```

The forced update detection is temporary test functionality. The intended production configuration is approximately:

```text
4 hours
```

The monitor and notification workflow have been tested end-to-end, including:

* MTGJSON update detection
* Windows toast notification
* Update Now activation
* MTGJSON database download
* gzip validation
* SHA-256 verification
* Database replacement
* Price Server shutdown
* Price Server restart
* Server health verification
* Successful completion of the update process

## Technology

* Microsoft Excel
* VBA
* Python
* Python `http.server`
* `ijson`
* REST APIs
* JSON
* MTGJSON
* JustTCG
* PyInstaller
* PowerShell
* Windows batch scripting
* Windows URI protocols
* Windows toast notifications

## Current Status

**Work in progress.**

The core inventory and pricing workflows are functional. The MTGJSON updater and monitoring system are also functional in their current test configuration.

### Working

**Inventory**

* Manual inventory entry
* Inventory search
* Card name, set, card number, quantity, condition, printing, and language fields

**Pricing**

* MTGJSON cached pricing
* Normal and foil MTGJSON pricing
* JustTCG live pricing
* Separate cached and live pricing workflows
* Pricing returned directly to Excel
* Price dates returned with pricing data

**Card Identification**

* MTGJSON UUID lookup
* TCGplayer Product ID lookup
* TCGplayer Product ID matching between MTGJSON and JustTCG
* Condition, printing, and language filters passed to JustTCG
* Card identity information returned to Excel
* Verification data returned to Excel

**MTGJSON**

* Streaming card database parsing
* Streaming pricing database parsing
* Reduced Price Server memory usage
* Database update utility
* SHA-256 verification
* Safe temporary database replacement
* Update result reporting

**MTGJSON Monitor**

* Background update monitoring
* Windows toast notifications
* Update Now and Later actions
* Windows URI protocol handling
* Price Server restart after successful updates
* Price Server health verification

**Application**

* Excel/VBA front end
* Python local HTTP server
* API communication between Excel and Python
* Local configuration for API credentials
* Authenticated local Price Server shutdown
* Server health checking
* PyInstaller build configuration
* Location-independent development startup workflow
* Python source and compiled EXE launch modes

### In Progress

**Excel Interface**

The core search and pricing workflow is functional. The Excel interface is continuing to be refined, including the presentation of pricing information and technical audit data.

**MTGJSON Monitoring**

The monitor is being transitioned from its short test configuration toward its intended production behavior, including approximately four-hour update checks and finalizing the background execution workflow.

**Security Hardening**

The backend currently uses localhost-only operation and authenticated local Price Server shutdown. Additional security hardening is planned before the project is considered production-ready.

## MTGJSON

MTGJSON is used as a local source of structured Magic: The Gathering card data and pricing information.

The project stores the required MTGJSON databases locally rather than requiring the application to download the complete datasets during normal operation.

The Price Server uses streaming parsing to extract only the card identity and pricing information required by the application.

The `MTGJSONUpdater` utility handles safe database updates using temporary downloads, gzip validation, and SHA-256 verification.

The `MTGJSONMonitor` provides background update detection and coordinates the update process when a new database version is detected.

## JustTCG

JustTCG is used for live card pricing.

The original implementation made API calls directly from Excel/Power Query while the API integration was being developed. Once the API implementation was working, the project was migrated to a Python backend.

The Python server now handles communication with JustTCG, keeping the API credentials and API-specific processing outside of the Excel workbook.

Live pricing requests are matched against the TCGplayer Product ID obtained from MTGJSON before a result is marked as verified.

## Development Challenge

One of the early challenges of the project was getting the JustTCG API integration working correctly through Power Query in the original Excel implementation.

That initial implementation provided the foundation for understanding the API and its responses. The pricing functionality was later migrated into Python as the project evolved toward a client/server architecture.

A more significant challenge was reconciling card identities between MTGJSON and JustTCG. Human-readable names and set information are not always consistent between data sources.

The solution was to use the TCGplayer Product ID as a cross-source identifier and validate the returned ID before accepting a live pricing result.

This also created a useful audit trail inside Excel, allowing the application to retain the identifiers and returned card information used to verify each live price.

### MTGJSON Memory Optimization

Another significant development challenge was the memory usage of the original MTGJSON loading implementation.

The initial implementation used Python's standard JSON parser to load the complete `AllPrintings.json.gz` and `AllPricesToday.json.gz` documents into memory.

Testing showed that this created substantial memory overhead, with the Price Server reaching approximately 1.8 GB of process memory during database loading.

The problem was addressed by replacing the full-document parsing approach with streaming JSON parsing using `ijson`.

The new implementation processes the compressed JSON incrementally and retains only the data required by the application.

Testing reduced the running Price Server to well under 200 MB while maintaining the same card lookup and pricing functionality.

This required testing the actual MTGJSON structure and resolving an additional issue where card records could be encountered before the corresponding set-name record during streaming. The final implementation temporarily associates cards with their set codes and resolves the human-readable set names after parsing.

### Automated Database Updates

The next major challenge was moving the MTGJSON update process from a manual utility into an automated background workflow.

The updater needed to safely handle large database files without leaving the application with a partially updated database. The solution was to download updates to temporary files, validate the gzip data, verify the SHA-256 hash against MTGJSON's published value, and only replace the existing database after all validation succeeded.

The monitoring system was then built around that updater. The monitor periodically checks MTGJSON for changes and coordinates the update process, Price Server shutdown and restart, and a final health check to confirm that the new databases have loaded successfully.

### Windows Notifications and URI Handling

Adding Windows toast notifications introduced another layer of complexity.

The initial notification implementation encountered an access-denied error when notifications were repeatedly created during background monitoring. This required investigating how the notification library managed its notifier and listener processes and changing the implementation to maintain a single notifier for the lifetime of the monitor process.

The next challenge was allowing notification buttons to trigger actions in the background monitor. The original approach relied on the notification library's internal callback mechanism, but this created conflicts with the application's own protocol handling.

The implementation was changed to use a registered Windows URI protocol:

```text
mtgjson-monitor://update
mtgjson-monitor://later
```

The monitor registers the protocol under the current Windows user and validates incoming URIs before performing any action.

### Troubleshooting the Notification Buttons

The most significant debugging issue encountered during the project so far came from the notification buttons themselves.

The buttons appeared correctly and could launch external URLs, but the custom `mtgjson-monitor://` actions did not initially reach the monitor's URI callback as expected.

The problem was ultimately traced to an interaction between the custom URI protocol and the notification library's internal callback system. The notification library derives an internal protocol identifier from its application name. The application had originally used `MTGJSON Monitor` as the notification application ID, which caused the library to interpret the application's own `mtgjson-monitor://` URI as one of its internal callbacks.

This resulted in the notification library intercepting the button activation before Windows could invoke the application's registered URI handler.

The issue was resolved by separating the notification library's internal application identifier from the application's custom URI protocol. The notification system now uses a different application identifier while the application continues to use:

```text
mtgjson-monitor://
```

for its own protocol.

This required testing the individual components separately, including direct URI activation, Windows registry registration, notification actions, and the complete update workflow.

The final system now successfully performs the complete workflow:

```text
MTGJSON update detected
        |
        v
Windows toast notification
        |
        v
Update Now
        |
        v
Windows URI protocol
        |
        v
MTGJSON Monitor callback
        |
        v
MTGJSONUpdater
        |
        v
Database validation and replacement
        |
        v
PriceServer restart
        |
        v
Health check
        |
        v
Update completed
```

This was the most involved troubleshooting process in the project to date and provided useful experience working with Windows process management, registry-based URI protocols, third-party Python libraries, background processes, and inter-process communication.

## Project Structure

```text
Card Pricing Prototype/
├── .gitignore
├── config.ini.example
├── mtgjson_monitor.py
├── MTGJSONUpdater.spec
├── PriceServer.spec
├── price_server.py
├── start_server.bat
├── Store - Inventory Test v2.xlsm
└── debug/
    ├── check_uuid.py
    ├── inspect_ijson.py
    ├── memory_test.py
    ├── test_ijson.py
    ├── test_prices.py
    ├── test_rhystic.py
    ├── test_set.py
    ├── test_sol_ring.py
    └── test_tcgplayerid.py
```

Generated databases, compiled executables, debug files, test environments, Python cache files, and local configuration files are excluded from version control.

The `debug/` directory contains one-off testing, inspection, troubleshooting, and development scripts that are not required by the application during normal operation.

## Quick Start

### Windows

1. Clone or download the repository.
2. Make sure Python 3 is installed if running the source files directly.
3. Install the required Python dependencies.
4. Copy `config.ini.example` to `config.ini`.
5. Add your JustTCG API key to `config.ini`.
6. Make sure the required MTGJSON databases are present in the `Data` directory.
7. Start the application using `start_server.bat`.
8. Select the desired startup mode:

   * **Python source** to run the development Python files directly.
   * **Compiled EXEs** to run locally built executables.
9. The startup process checks the MTGJSON databases, starts the Price Server, waits for the server health check, starts the MTGJSON Monitor, and opens the Excel workbook.

The source repository does not require compiled executables to run the Python development workflow.

Compiled executables can be generated locally using the included PyInstaller `.spec` files when testing the packaged build.

### Python Dependencies

The current Python backend requires:

```text
ijson
```

Install the required package with:

```text
pip install ijson
```

Additional dependencies are required by the MTGJSON Monitor for its Windows notification functionality.

### Configuration

Create:

```text
config.ini
```

from:

```text
config.ini.example
```

Then configure the JustTCG API key:

```ini
[JustTCG]
api_key=YOUR_JUSTTCG_API_KEY
```

The API key is stored outside the Excel workbook and `config.ini` is excluded from version control.

### First Run

The normal development startup workflow is:

```text
start_server.bat
       |
       v
Select Python source or compiled EXEs
       |
       v
MTGJSON database check
       |
       v
PriceServer starts
       |
       v
/health reports ready
       |
       v
MTGJSON Monitor starts
       |
       v
Excel workbook opens
```

Once the workbook is open, inventory can be entered and pricing requests can be performed through the Excel interface.

## Running the Project

The development Windows workflow is:

```text
start_server.bat
       |
       v
Select startup mode
       |
       +--------------------+
       |                    |
       v                    v
Python source          Compiled EXEs
       |                    |
       +---------+----------+
                 |
                 v
        MTGJSON database check
                 |
                 v
            PriceServer
                 |
                 v
             /health
                 |
                 v
          MTGJSON Monitor
                 |
                 v
         Excel inventory
            workbook
```

The `start_server.bat` launcher is designed to be location-independent. It uses paths relative to the location of the batch file rather than requiring a specific drive letter or installation directory.

This allows the repository to be cloned or moved to different directories and drives without changing the startup configuration.

The launcher provides two development modes.

**Python source mode**

Runs the Python source files directly:

```text
update_mtgjson.py
price_server.py
mtgjson_monitor.py
```

**Compiled EXE mode**

Runs locally built executables when they are available:

```text
MTGJSONUpdater.exe
PriceServer.exe
MTGJSONMonitor.exe
```

The compiled executables are development/build artifacts and are not required when using Python source mode.

The launcher performs the initial MTGJSON database check before starting the Price Server. It then waits for the Price Server health endpoint to report that the server is ready before starting the MTGJSON Monitor and opening the Excel workbook.

During development, the Python source files can also be run individually when troubleshooting specific components.

The Excel workbook communicates with the local Python server through:

```text
http://127.0.0.1:5000
```

## Why I Built It

I originally built this project to create something useful for an LGS while expanding my knowledge of Python and API development.

The project evolved beyond its original purpose into a practical exercise in connecting several different technologies into a working application.

More than anything, I'm proud that it became a working product rather than remaining a collection of experiments.

I continue to develop it in my spare time as a way to learn, experiment, and potentially build something that other people may find useful.

## Future Development

The project will continue to evolve as new ideas and requirements are explored.

Planned development includes:

* CSV inventory imports
* Database-assisted card entry
* Duplicate inventory consolidation
* Production four-hour MTGJSON update checks
* Final background monitor execution
* Full inventory valuation
* Additional inventory management functionality
* Further improvements to the Excel interface
* Additional pricing and inventory workflows
* Additional error handling
* JustTCG API key protection using Windows credential protection
* Additional validation of returned JustTCG variants
* Review of local inter-process authentication
* General security review of the Excel-to-Python communication workflow
* Dedicated application launcher to replace the development batch workflow
* Cross-platform application architecture

## Author

Alec West

## Disclaimer

This is an independent personal project and is not affiliated with MTGJSON or JustTCG.

Pricing and card data are provided by external services and may change independently of this project.
