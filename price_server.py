import json
import configparser
import urllib.parse
import urllib.request
import urllib.error
import gzip
import sys
import secrets
import ijson
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

CONFIG_FILE = BASE_DIR / "config.ini"
DATA_DIR = BASE_DIR / "Data"

ALL_PRINTINGS_FILE = DATA_DIR / "AllPrintings.json.gz"
ALL_PRICES_FILE = DATA_DIR / "AllPricesToday.json.gz"

config = configparser.ConfigParser()

if not CONFIG_FILE.exists():
    raise FileNotFoundError(
        f"Missing config.ini at: {CONFIG_FILE}"
    )

config.read(CONFIG_FILE)

try:
    API_KEY = config["JustTCG"]["api_key"].strip()
except KeyError:
    raise RuntimeError(
        "config.ini is missing [JustTCG] api_key"
    )

if not API_KEY or API_KEY == "YOUR_API_KEY":
    raise RuntimeError(
        "Replace YOUR_API_KEY in config.ini with your JustTCG API key."
    )


JUSTTCG_URL = "https://api.justtcg.com/v1/cards"

HOST = "127.0.0.1"
PORT = 5000

SERVER_STATUS = "starting"
SERVER_MESSAGE = "Starting price server..."

SHUTDOWN_TOKEN_FILE = (
    DATA_DIR / "PriceServerShutdownToken"
)

SHUTDOWN_TOKEN = None


# ---------------------------------------------------------
# MTGJSON Data
# ---------------------------------------------------------

MTGJSON_CARDS = {}
MTGJSON_TCGPLAYER_IDS = {}
MTGJSON_PRICES = {}


def load_mtgjson():
    """
    Stream MTGJSON card and pricing data into memory.
    """
    global SERVER_STATUS, SERVER_MESSAGE

    SERVER_STATUS = "loading"
    SERVER_MESSAGE = "Loading MTGJSON data..."

    print("")
    print("----------------------------------------")
    print("Loading MTGJSON")
    print("----------------------------------------")

    if not ALL_PRINTINGS_FILE.exists():
        raise FileNotFoundError(
            f"Missing MTGJSON file: {ALL_PRINTINGS_FILE}"
        )

    if not ALL_PRICES_FILE.exists():
        raise FileNotFoundError(
            f"Missing MTGJSON file: {ALL_PRICES_FILE}"
        )

    SERVER_MESSAGE = "Loading card database..."

    # -----------------------------------------------------
    # Load AllPrintings
    # -----------------------------------------------------

    print("Loading AllPrintings.json.gz...")

    card_count = 0

    # Map MTGJSON set codes to human-readable set names.
    set_names = {}

    # Temporarily store cards by set code.
    card_records = []

    current_card_name = ""
    current_card_number = ""
    current_card_uuid = ""
    current_tcgplayer_id = ""
    current_card_set_code = ""

    in_card = False

    with gzip.open(
        ALL_PRINTINGS_FILE,
        "rb"
    ) as file:

        parser = ijson.parse(file)

        for prefix, event, value in parser:

            # ---------------------------------------------
            # Set name
            # ---------------------------------------------

            if (
                event == "string"
                and prefix.startswith("data.")
                and prefix.endswith(".name")
                and prefix.count(".") == 2
            ):

                set_code = prefix.split(".")[1]

                set_names[set_code] = value

                continue

            # ---------------------------------------------
            # Start of card
            # ---------------------------------------------

            if (
                event == "start_map"
                and prefix.endswith(".cards.item")
            ):

                in_card = True

                current_card_name = ""
                current_card_number = ""
                current_card_uuid = ""
                current_tcgplayer_id = ""
                current_card_set_code = ""

                continue

            if not in_card:
                continue

            # ---------------------------------------------
            # Card fields
            # ---------------------------------------------

            if (
                event == "string"
                and prefix.endswith(".cards.item.name")
            ):

                current_card_name = value

            elif (
                event in ("string", "number")
                and prefix.endswith(".cards.item.number")
            ):

                current_card_number = str(value)

            elif (
                event == "string"
                and prefix.endswith(".cards.item.uuid")
            ):

                current_card_uuid = value

            elif (
                event in ("string", "number")
                and prefix.endswith(
                    ".cards.item.identifiers.tcgplayerProductId"
                )
            ):

                current_tcgplayer_id = str(value)

            elif (
                event == "string"
                and prefix.endswith(".cards.item.setCode")
            ):

                current_card_set_code = value

            # ---------------------------------------------
            # End of card
            # ---------------------------------------------

            if (
                event == "end_map"
                and prefix.endswith(".cards.item")
            ):

                if current_card_uuid:

                    card_records.append(
                        (
                            current_card_name,
                            current_card_number,
                            current_card_uuid,
                            current_tcgplayer_id,
                            current_card_set_code
                        )
                    )

                in_card = False

    # -----------------------------------------------------
    # Build card lookup using set names
    # -----------------------------------------------------

    for (
        card_name,
        card_number,
        card_uuid,
        tcgplayer_id,
        set_code
    ) in card_records:

        set_name = set_names.get(
            set_code,
            ""
        )

        if not set_name:
            continue

        key = (
            card_name.lower(),
            set_name.lower(),
            card_number.lower()
        )

        MTGJSON_CARDS[key] = card_uuid

        if tcgplayer_id:

            MTGJSON_TCGPLAYER_IDS[key] = (
                tcgplayer_id
            )

        card_count += 1

    # Release temporary card records.
    del card_records

    print(
        f"Loaded {card_count:,} card records."
    )

    print("Loading AllPricesToday...")
    print("Loading AllPricesToday.json.gz...")

    price_count = 0

    with gzip.open(
        ALL_PRICES_FILE,
        "rb"
    ) as file:

        parser = ijson.parse(file)

        for prefix, event, value in parser:

            if event not in ("number", "string"):
                continue

            parts = prefix.split(".")

            # Expected:
            #
            # data.UUID.paper.tcgplayer.retail.normal.DATE
            # data.UUID.paper.tcgplayer.retail.foil.DATE

            if len(parts) != 7:
                continue

            if parts[0] != "data":
                continue

            if parts[2] != "paper":
                continue

            if parts[3] != "tcgplayer":
                continue

            if parts[4] != "retail":
                continue

            price_type = parts[5]

            if price_type not in ("normal", "foil"):
                continue

            uuid = parts[1]
            price_date = parts[6]

            if not uuid or not price_date:
                continue

            try:
                price = float(value)
            except (TypeError, ValueError):
                continue

            if uuid not in MTGJSON_PRICES:
                MTGJSON_PRICES[uuid] = {}

            MTGJSON_PRICES[uuid][price_type] = {
                "price": price,
                "date": price_date
            }

            price_count += 1

    print(
        f"Loaded {len(MTGJSON_PRICES):,} price records."
    )

    print(
        f"  Price entries processed: "
        f"{price_count:,}"
    )

    print("MTGJSON ready.")
    print("----------------------------------------")
    print("")

    SERVER_STATUS = "ready"
    SERVER_MESSAGE = "Price server ready."

def get_mtgjson_price(request_data):
    """
    Find the MTGJSON price for a card.
    """

    card_name = str(
        request_data.get("cardName", "")
    ).strip()

    set_name = str(
        request_data.get("set", "")
    ).strip()

    card_number = str(
        request_data.get("cardNumber", "")
    ).strip()

    printing = str(
        request_data.get("printing", "")
    ).strip()

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    missing = []

    if not card_name:
        missing.append("cardName")

    if not set_name:
        missing.append("set")

    if not card_number:
        missing.append("cardNumber")

    if not printing:
        missing.append("printing")

    if missing:

        raise ValueError(
            "Missing required fields: "
            + ", ".join(missing)
        )

    # -----------------------------------------------------
    # Find UUID
    # -----------------------------------------------------

    key = (
        card_name.lower(),
        set_name.lower(),
        card_number.lower()
    )

    uuid = MTGJSON_CARDS.get(key)
    tcgplayer_id = MTGJSON_TCGPLAYER_IDS.get(key)

    if not uuid:

        return {
            "success": False,
            "error": (
                "Card was not found in the MTGJSON "
                "card database."
            )
        }

    # -----------------------------------------------------
    # Find price record
    # -----------------------------------------------------

    price_data = MTGJSON_PRICES.get(uuid)

    if not price_data:

        return {
            "success": False,
            "error": (
                "No MTGJSON price data was found "
                "for this card."
            )
        }

    # -----------------------------------------------------
    # Determine printing
    # -----------------------------------------------------

    printing_lower = printing.lower()

    if printing_lower == "foil":

        price_type = "foil"

    else:

        price_type = "normal"

    price_record = price_data.get(
        price_type
    )

    if not price_record:

        return {
            "success": False,
            "error": (
                f"No MTGJSON {price_type} price "
                "was found for this card."
            )
        }

    # -----------------------------------------------------
    # Get price
    # -----------------------------------------------------

    price = price_record.get(
        "price"
    )

    latest_date = price_record.get(
        "date"
    )

    if price is None or latest_date is None:

        return {
            "success": False,
            "error": (
                "MTGJSON price data was incomplete."
            )
        }
    # -----------------------------------------------------
    # Return result
    # -----------------------------------------------------

    return {
        "success": True,
        "cardName": card_name,
        "set": set_name,
        "cardNumber": card_number,
        "printing": printing,
        "uuid": uuid,
        "tcgplayerId": tcgplayer_id,
        "price": float(price),
        "date": latest_date
    }


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def send_json(handler, status_code, data):
    """Send a JSON response to the Excel client."""

    response = json.dumps(data).encode("utf-8")

    handler.send_response(status_code)
    handler.send_header(
        "Content-Type",
        "application/json"
    )
    handler.send_header(
        "Content-Length",
        str(len(response))
    )
    handler.end_headers()

    handler.wfile.write(response)

def initialize_shutdown_token():
    """
    Create a random authentication token for controlled
    PriceServer shutdown.

    The token is stored locally so the MTGJSON monitor can
    authenticate its shutdown request.
    """

    global SHUTDOWN_TOKEN

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    SHUTDOWN_TOKEN = secrets.token_urlsafe(32)

    try:

        with open(
            SHUTDOWN_TOKEN_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                SHUTDOWN_TOKEN
            )

    except Exception as error:

        raise RuntimeError(
            "Unable to create PriceServer shutdown "
            f"authentication token: {error}"
        )

    print(
        "PriceServer shutdown authentication initialized."
    )

def is_shutdown_authorized(handler):
    """
    Validate the authentication token supplied by the
    MTGJSON monitor.
    """

    supplied_token = handler.headers.get(
        "X-PriceServer-Token",
        ""
    )

    if not supplied_token:
        return False

    return secrets.compare_digest(
        supplied_token,
        SHUTDOWN_TOKEN or ""
    )

def request_server_shutdown():
    """
    Request the HTTP server to shut down cleanly.

    HTTPServer.shutdown() must be called from a thread
    other than the thread currently running serve_forever().
    """

    import threading

    def shutdown():
        print("")
        print("Shutdown requested.")
        print("Stopping price server...")

        server.shutdown()

    threading.Thread(
        target=shutdown,
        daemon=True
    ).start()

def get_price_from_justtcg(card_data):
    """
    Find the first matching variant returned by JustTCG.

    The request already filters by condition, printing,
    and language, so the first returned variant should
    represent the requested combination.
    """

    if not isinstance(card_data, dict):
        return None

    cards = card_data.get("data", [])

    if not cards:
        return None

    for card in cards:

        variants = card.get("variants", [])

        if not variants:
            continue

        for variant in variants:

            price = variant.get("price")

            if price is not None:

                last_updated = variant.get(
                    "lastUpdated"
                )

                date = ""
                
                if last_updated:
                    date = datetime.fromtimestamp(
                        last_updated,
                        timezone.utc
                    ).strftime("%Y-%m-%d")

                return {
                    "price": float(price),
                    "date": date,
                    "card_name": card.get(
                        "name",
                        ""
                    ),
                    "set_name": card.get(
                        "set_name",
                        ""
                    ),
                    "card_number": card.get(
                        "number",
                        ""
                    ),
                    "condition": variant.get(
                        "condition",
                        ""
                    ),
                    "printing": variant.get(
                        "printing",
                        ""
                    ),
                    "language": variant.get(
                        "language",
                        "English"
                    ) or "English",
                    "mtgjsonId": card.get(
                        "mtgjsonId",
                        ""
                    ),
                    "tcgplayerId": card.get(
                        "tcgplayerId",
                        ""
                    ),
                    "scryfallId": card.get(
                        "scryfallId",
                        ""
                    )
                }

    return None


def lookup_price(request_data):
    """
    Find the exact card in MTGJSON, obtain its TCGplayer
    Product ID, and use that ID to retrieve live pricing
    from JustTCG.
    """

    card_name = str(
        request_data.get("cardName", "")
    ).strip()

    set_name = str(
        request_data.get("set", "")
    ).strip()

    card_number = str(
        request_data.get("cardNumber", "")
    ).strip()

    condition = str(
        request_data.get("condition", "")
    ).strip()

    printing = str(
        request_data.get("printing", "")
    ).strip()

    language = str(
        request_data.get("language", "")
    ).strip()

    # -----------------------------------------------------
    # Basic validation
    # -----------------------------------------------------

    missing = []

    if not card_name:
        missing.append("cardName")

    if not set_name:
        missing.append("set")

    if not card_number:
        missing.append("cardNumber")

    if not condition:
        missing.append("condition")

    if not printing:
        missing.append("printing")

    if not language:
        missing.append("language")

    if missing:

        raise ValueError(
            "Missing required fields: "
            + ", ".join(missing)
        )

    # -----------------------------------------------------
    # Find exact card in MTGJSON
    # -----------------------------------------------------

    key = (
        card_name.lower(),
        set_name.lower(),
        card_number.lower()
    )

    uuid = MTGJSON_CARDS.get(key)

    if not uuid:

        return {
            "success": False,
            "error": (
                "Card was not found in the MTGJSON "
                "card database."
            )
        }

    # -----------------------------------------------------
    # Find TCGplayer Product ID
    # -----------------------------------------------------

    tcgplayer_id = MTGJSON_TCGPLAYER_IDS.get(key)

    if not tcgplayer_id:

        return {
            "success": False,
            "error": (
                "No TCGplayer Product ID was found "
                "for this card in the MTGJSON database."
            ),
            "uuid": uuid
        }

    # -----------------------------------------------------
    # Build JustTCG query using TCGplayer Product ID
    # -----------------------------------------------------

    params = {
        "tcgplayerId": tcgplayer_id,
        "condition": condition,
        "printing": printing,
        "language": language
    }

    query_string = urllib.parse.urlencode(
        params
    )

    url = JUSTTCG_URL + "?" + query_string

    print("")
    print("JustTCG lookup")
    print("----------------------------------------")
    print(f"Card:            {card_name}")
    print(f"Set:             {set_name}")
    print(f"Number:          {card_number}")
    print(f"MTGJSON UUID:    {uuid}")
    print(f"TCGplayer ID:    {tcgplayer_id}")
    print(f"Condition:       {condition}")
    print(f"Printing:        {printing}")
    print(f"Language:        {language}")
    print("----------------------------------------")

    request = urllib.request.Request(
        url,
        headers={
            "x-api-key": API_KEY,
            "Accept": "application/json"
        },
        method="GET"
    )

    # -----------------------------------------------------
    # Make API request
    # -----------------------------------------------------

    try:

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            status = response.status

            body = response.read().decode(
                "utf-8"
            )

    except urllib.error.HTTPError as error:

        error_body = ""

        try:
            error_body = error.read().decode(
                "utf-8"
            )
        except Exception:
            pass

        print(
            f"JustTCG HTTP ERROR: {error.code}"
        )

        print(
            f"JustTCG RESPONSE: {error_body}"
        )

        raise RuntimeError(
            f"JustTCG returned HTTP "
            f"{error.code}: {error_body}"
        )

    except urllib.error.URLError as error:

        raise RuntimeError(
            "Unable to connect to JustTCG: "
            f"{error.reason}"
        )

    except TimeoutError:

        raise RuntimeError(
            "The JustTCG request timed out."
        )

    if status != 200:

        raise RuntimeError(
            f"JustTCG returned HTTP "
            f"{status}: {body}"
        )

    # -----------------------------------------------------
    # Parse JSON
    # -----------------------------------------------------

    try:

        data = json.loads(body)

    except json.JSONDecodeError:

        raise RuntimeError(
            "JustTCG returned invalid JSON."
        )

    # -----------------------------------------------------
    # Validate returned card identity
    # -----------------------------------------------------

    cards = data.get("data", [])

    if not cards:

        return {
            "success": False,
            "error": (
                "JustTCG returned no card for "
                f"TCGplayer Product ID {tcgplayer_id}."
            ),
            "uuid": uuid,
            "tcgplayerId": tcgplayer_id
        }

    justtcg_card = cards[0]

    returned_tcgplayer_id = str(
        justtcg_card.get(
            "tcgplayerId",
            ""
        )
    )

    if returned_tcgplayer_id != str(tcgplayer_id):

        return {
            "success": False,
            "error": (
                "JustTCG returned a different "
                "TCGplayer Product ID than expected."
            ),
            "uuid": uuid,
            "tcgplayerId": tcgplayer_id,
            "returnedTcgplayerId": returned_tcgplayer_id
        }

    # -----------------------------------------------------
    # Extract requested variant
    # -----------------------------------------------------

    result = get_price_from_justtcg(
        data
    )

    if result is None:

        return {
            "success": False,
            "error": (
                "No matching price was found "
                "for this card, condition, "
                "printing, and language."
            ),
            "uuid": uuid,
            "tcgplayerId": tcgplayer_id
        }

    # -----------------------------------------------------
    # Return validated result
    # -----------------------------------------------------

    return {
        "success": True,
        "verified": True,
        "cardName": card_name,
        "set": set_name,
        "cardNumber": card_number,
        "uuid": uuid,
        "tcgplayerId": tcgplayer_id,
        "price": result["price"],
        "date": result["date"],
        "condition": result["condition"],
        "printing": result["printing"],
        "language": result["language"],
        "justtcgName": result["card_name"],
        "justtcgSet": result["set_name"],
        "justtcgNumber": result["card_number"]
    }


# ---------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------

class PriceRequestHandler(
    BaseHTTPRequestHandler
):

    def log_message(self, format, *args):

        print(
            f"{self.address_string()} - "
            f"{format % args}"
        )

    def do_GET(self):
        if self.path == "/health":

            if SERVER_STATUS == "ready":
                send_json(
                    self,
                    200,
                    {
                        "success": True,
                        "status": "ready",
                        "server": "JustTCG Price Server",
                        "message": SERVER_MESSAGE
                    }
                )
            else:
                send_json(
                    self,
                    200,
                    {
                        "success": False,
                        "status": SERVER_STATUS,
                        "server": "JustTCG Price Server",
                        "message": SERVER_MESSAGE
                    }
                )

            return

        send_json(
            self,
            404,
            {
                "success": False,
                "error": "Endpoint not found."
            }
        )

    def do_POST(self):

        # -------------------------------------------------
        # Controlled server shutdown
        # -------------------------------------------------

        if self.path == "/shutdown":

            if self.client_address[0] != "127.0.0.1":

                send_json(
                    self,
                    403,
                    {
                        "success": False,
                        "error": "Shutdown is only available locally."
                    }
                )

                return

            if not is_shutdown_authorized(self):

                send_json(
                    self,
                    403,
                    {
                        "success": False,
                        "error": "Shutdown authentication failed."
                    }
                )

                return

            send_json(
                self,
                200,
                {
                    "success": True,
                    "message": "Price server shutdown requested."
                }
            )

            request_server_shutdown()

            return

        # -------------------------------------------------
        # Determine endpoint
        # -------------------------------------------------

        if self.path not in (
            "/get-price",
            "/get-mtgjson-price"
        ):

            send_json(
                self,
                404,
                {
                    "success": False,
                    "error": "Endpoint not found."
                }
            )

            return

        try:

            # -------------------------------------------------
            # Read request body
            # -------------------------------------------------

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            if content_length <= 0:

                raise ValueError(
                    "Request body is empty."
                )

            if content_length > 64 * 1024:
                raise ValueError(
                    "Request body is too large."
                )

            body = self.rfile.read(
                content_length
            ).decode("utf-8")

            # -------------------------------------------------
            # Parse JSON
            # -------------------------------------------------

            try:

                request_data = json.loads(
                    body
                )

            except json.JSONDecodeError:

                raise ValueError(
                    "Invalid JSON received "
                    "from Excel."
                )

            # -------------------------------------------------
            # Perform lookup
            # -------------------------------------------------

            if self.path == "/get-price":

                result = lookup_price(
                    request_data
                )

            else:

                result = get_mtgjson_price(
                    request_data
                )

            send_json(
                self,
                200,
                result
            )

        except ValueError as error:

            send_json(
                self,
                400,
                {
                    "success": False,
                    "error": str(error)
                }
            )

        except RuntimeError as error:

            send_json(
                self,
                502,
                {
                    "success": False,
                    "error": str(error)
                }
            )

        except Exception as error:

            print(
                "Unexpected server error:",
                error
            )

            send_json(
                self,
                500,
                {
                    "success": False,
                    "error":
                        "Unexpected server error."
                }
            )


# ---------------------------------------------------------
# Start Server
# ---------------------------------------------------------

if __name__ == "__main__":

    # -----------------------------------------------------
    # Load MTGJSON before starting server
    # -----------------------------------------------------

    load_mtgjson()

    # -----------------------------------------------------
    # Initialize shutdown authentication
    # -----------------------------------------------------

    initialize_shutdown_token()

    server = HTTPServer(
        (HOST, PORT),
        PriceRequestHandler
    )

    print("----------------------------------------")
    print("MTG Price Server")
    print("----------------------------------------")
    print(
        f"Listening on "
        f"http://{HOST}:{PORT}"
    )

    print("")
    print("Health check:")
    print(
        f"http://{HOST}:{PORT}/health"
    )

    print("")
    print("Endpoints:")
    print(
        "  /get-price          = JustTCG"
    )
    print(
        "  /get-mtgjson-price  = MTGJSON"
    )

    print("")
    print("Press Ctrl+C to stop.")
    print("----------------------------------------")

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print("")
        print("Stopping server...")

    finally:

        server.server_close()