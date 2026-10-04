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
* Match cards between MTGJSON and JustTCG using TCGplayer Product IDs
* Verify returned JustTCG pricing against the expected TCGplayer Product ID
* Return pricing and verification data to Excel
* Maintain local MTGJSON databases
* Check for updated MTGJSON data
* Monitor MTGJSON for database updates in the background
* Notify the user when an MTGJSON update is available
* Start an MTGJSON update from a Windows notification
* Automatically restart the local Price Server after a successful database update
* Verify that the restarted Price Server is healthy before completing the update process
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
MTGJSONUpdater
    |
    | Successful database update
    v
PriceServer Restart
    |
    v
Health Check
```

The Excel front end handles inventory management and user interaction while the Python backend handles local database access, API communication, cross-source card verification, and database maintenance.

The MTGJSON Monitor runs separately from the Price Server and is responsible for detecting database updates and coordinating the update and restart process.

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

The project now includes a background MTGJSON monitoring process.

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

The MTGJSON Monitor is currently in an active test phase.

The current development configuration uses a short check interval and forced update detection so that the notification and update workflow can be repeatedly tested without waiting for an actual MTGJSON release.

The current test interval is approximately:

```text
30 seconds
```

The forced update detection is temporary test functionality and will be replaced with the intended production update-check behavior after testing is complete.

The intended production configuration is approximately:

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

The core application and pricing workflows are functional. The MTGJSON update monitoring and notification system is functional in its current test configuration, while several inventory-management features and production update behaviors remain under development.

### Working

**Inventory**

* Manual inventory entry
* Inventory search
* Card name, set, card number, quantity, condition, printing, and language fields

**Pricing**

* MTGJSON cached pricing
* JustTCG live pricing
* Separate workflows for cached and live pricing
* Pricing returned directly to the Excel interface

**Card Identification**

* MTGJSON UUID lookup
* TCGplayer Product ID lookup
* TCGplayer Product ID matching between MTGJSON and JustTCG
* Card number verification
* Condition verification
* Printing verification
* Language verification
* Verification data returned to Excel

**MTGJSON**

* Local card database
* Local pricing database
* Database update utility
* Remote SHA-256 update detection
* Temporary download and validation
* SHA-256 verification
* Database replacement after successful validation
* Update result reporting

**MTGJSON Monitor**

* Background MTGJSON monitoring
* Windows toast notifications
* Update Now notification action
* Later notification action
* Windows URI protocol handling
* Automatic Price Server restart after successful updates
* Price Server health verification after restart
* Test-phase forced update detection

**Application**

* Excel/VBA front end
* Python local HTTP server
* API communication between Excel and Python
* Local configuration for API credentials
* Server health checking
* PyInstaller build configuration
* Windows batch startup workflow

### In Progress

**Excel Interface**

The core search and pricing workflow is functional. The Excel interface is continuing to be refined, including the presentation of pricing information and the handling of technical audit data.

The workbook maintains detailed verification information so that pricing results can be traced back to the identifiers used by the backend.

**MTGJSON Monitoring**

The monitoring and notification workflow is currently being tested using a short update interval and forced update detection.

The next stage is transitioning the monitor from the test configuration to its intended production behavior, including approximately four-hour update checks and finalizing the background execution workflow.

### Planned

**Inventory Import**

* CSV imports from multiple sources
* Additional methods for bulk inventory entry

**Card Entry Tool**

A dedicated card-entry sheet that can query the local database and allow cards to be selected based on search criteria rather than requiring all identifying information to be entered manually.

**Duplicate Consolidation**

A data-processing step that will combine duplicate cards entered into inventory into a single line item and update the quantity accordingly.

**Production Database Monitoring**

The current MTGJSON monitoring system is functional in its test configuration.

Planned production behavior includes:

* Four-hour update checks
* Automatic database updates
* Continued background operation
* Final notification and startup behavior
* Additional error handling and recovery

**Inventory Valuation**

A complete inventory valuation system using card quantities and current pricing data.

## MTGJSON

MTGJSON is used as a local source of structured Magic: The Gathering card data and pricing information.

The project stores the required MTGJSON databases locally rather than requiring the application to download the complete datasets during normal operation.

The `MTGJSONUpdater` utility checks the remote files for changes and updates the local databases when appropriate.

The `MTGJSONMonitor` periodically checks for changes and coordinates the update process when a new database version is detected.

During the current test phase, the monitor uses a short check interval and forced update detection. The production configuration is intended to check approximately every four hours.

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

### Automated Database Updates

The next major challenge was moving the MTGJSON update process from a manual utility into an automated background workflow.

The updater itself needed to safely handle large database files without leaving the application with a partially updated database. The solution was to download updates to temporary files, validate the gzip data, verify the SHA-256 hash against MTGJSON's published value, and only replace the existing database after all validation succeeded.

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

The monitor registers the protocol under the current Windows user and validates incoming URIs before performing any action. This allows Windows notification buttons to invoke the monitor without exposing update functionality directly through the notification library.

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

This required testing the individual components separately, including direct URI activation, Windows registry registration, notification actions, and the complete update workflow. Once isolated, the underlying Windows URI mechanism was confirmed to be working correctly and the conflict with the notification library was identified as the source of the problem.

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
├── check_uuid.py
├── mtgjson_monitor.py
├── MTGJSONUpdater.spec
├── PriceServer.spec
├── price_server.py
├── start_server.bat
└── Store - Inventory Test v2.xlsm
```

Generated databases, compiled executables, debug files, test environments, Python cache files, and local configuration files are excluded from version control.

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

The project is designed to be started using `start_server.bat`.

The batch file starts the MTGJSON updater, launches the Price Server, waits for the server to become available, and then opens the Excel workbook.

The compiled `MTGJSONUpdater.exe` and `PriceServer.exe` files are required for `start_server.bat` to run. These executables are generated from the included PyInstaller `.spec` files and are included in the packaged version of the application.

The MTGJSON Monitor is currently being tested separately from the normal startup workflow. During development, the Python source files can be run directly.

For development, the Python source files can be run directly, or the executables can be rebuilt using the included `.spec` files.

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

Some of the planned development includes:

* CSV inventory imports
* Database-assisted card entry
* Duplicate inventory consolidation
* Four-hour MTGJSON update checks
* Production automatic database updates
* Finalize background monitor execution
* Full inventory valuation
* Additional inventory management functionality
* Further improvements to the Excel interface
* Additional pricing and inventory workflows
* Additional error handling and security hardening

## Author

Alec West

## Disclaimer

This is an independent personal project and is not affiliated with MTGJSON or JustTCG.

Pricing and card data are provided by external services and may change independently of this project.

