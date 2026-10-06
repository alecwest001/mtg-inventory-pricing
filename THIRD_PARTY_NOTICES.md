# Third-Party Notices

This file documents third-party services, data sources, libraries, and other materials used by the MTG Inventory & Pricing Prototype.

This project is independent and is not affiliated with or endorsed by any of the third parties listed below.

Users are responsible for complying with the applicable licenses, terms of service, and usage requirements for third-party software, data, and services.

---

## MTGJSON

**Website:** https://mtgjson.com/
**License:** MIT License
**License Information:** https://www.mtgjson.com/license/

This project uses MTGJSON data for Magic: The Gathering card information, including card identities, set information, card identifiers, and related data.

MTGJSON is an independent open-source project. MTGJSON's license applies to MTGJSON's own software and data and is separate from the license for this project.

Please refer to the official MTGJSON license for the current terms and requirements.

---

## JustTCG

**Website:** https://justtcg.com/
**Terms of Service:** https://justtcg.com/terms
**Commercial Use:** https://justtcg.com/docs/commercial-use

This project optionally uses the JustTCG API to retrieve live Magic: The Gathering pricing information.

This project does not provide, distribute, or embed a JustTCG API key. Users must provide and configure their own API credentials.

Use of the JustTCG API and its data is subject to the applicable JustTCG Terms of Service and the subscription associated with the user's API account. Users are responsible for ensuring that their use complies with applicable commercial-use, licensing, attribution, rate-limit, and other requirements.

This project does not resell or redistribute the JustTCG raw pricing feed and is not intended to operate as a competing pricing API.

---

## Python

**Website:** https://www.python.org/
**License:** Python Software Foundation License
**License Information:** https://docs.python.org/3/license.html

This project is developed using Python and may distribute compiled Python applications using PyInstaller.

Python remains a separate third-party software project and is subject to its own licensing terms.

---

## winotify

**Repository:** https://github.com/versa-syahptr/winotify
**License:** MIT License

This project uses `winotify` to provide Windows toast notifications for the MTGJSON database update monitor.

`winotify` is an independent open-source project and is subject to its own license.

The upstream project identifies itself as MIT licensed.

---

## ijson

**Repository:** https://github.com/ICRAR/ijson
**License:** BSD-style license
**Additional Component:** YAJL license

This project uses `ijson` for incremental parsing of large JSON data files. Streaming parsing allows the application to process the MTGJSON databases without loading the entire JSON structure into memory.

The `ijson` distribution includes its own BSD-style license as well as licensing terms for the YAJL component used by certain parser backends. The upstream `LICENSE.txt` should be consulted for the complete applicable terms.

See the upstream repository for the current license information.

---

## PyInstaller

**Website:** https://pyinstaller.org/
**License:** GPL 2.0 with exception; Apache 2.0 for certain files

PyInstaller is used to build standalone Windows executables from the Python application.

PyInstaller uses a dual-licensing scheme. The GPL 2.0 license includes an exception permitting PyInstaller to be used to bundle applications, including commercial applications. Certain files are covered by the Apache License 2.0.

See the official PyInstaller license documentation for the current terms.

---

## Microsoft Excel

**Website:** https://www.microsoft.com/microsoft-365/excel

The current prototype uses Microsoft Excel and VBA as part of its user interface and application workflow.

Microsoft Excel and VBA are proprietary Microsoft products. This project does not distribute Microsoft Excel or Microsoft VBA.

Users must have an appropriately licensed installation of Microsoft Excel to use the Excel-based interface.

---

## Magic: The Gathering

Magic: The Gathering and related names, card names, artwork, characters, and trademarks are property of their respective owners, including Wizards of the Coast and/or its licensors.

This project is an independent community project and is not affiliated with or endorsed by Wizards of the Coast.

The project does not claim ownership of third-party Magic: The Gathering intellectual property.

---

## TCGplayer

**Website:** https://www.tcgplayer.com/

This project may use TCGplayer Product IDs as identifiers when reconciling card information between data sources.

TCGplayer and related trademarks are property of their respective owners.

This project is not affiliated with or endorsed by TCGplayer.

---

## Disclaimer

Third-party names, trademarks, software, APIs, data, and other materials remain the property of their respective owners.

Third-party licenses and terms may change over time. The links and descriptions in this document are provided for reference and do not replace the applicable third-party licenses, terms of service, or other official documentation.

Where a third-party license or terms conflict with information in this document, the applicable third-party license or official terms take precedence.
