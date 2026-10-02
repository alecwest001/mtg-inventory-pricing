import json
import configparser
import urllib.parse
import urllib.request
import urllib.error
import gzip
import sys
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


# ---------------------------------------------------------
# MTGJSON Data
# ---------------------------------------------------------

MTGJSON_CARDS = {}
MTGJSON_TCGPLAYER_IDS = {}
MTGJSON_PRICES = {}


def load_mtgjson():
    """
    Load AllPrintings and AllPricesToday into memory.
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

    with gzip.open(
        ALL_PRINTINGS_FILE,
        "rt",
        encoding="utf-8"
    ) as file:

        all_printings = json.load(file)

    card_count = 0

    for set_data in all_printings.get("data", {}).values():

        set_name = set_data.get("name", "")

        for card in set_data.get("cards", []):

            card_name = card.get("name", "")
            card_number = str(card.get("number", ""))

            uuid = card.get("uuid")

            if not uuid:
                continue

            key = (
                card_name.lower(),
                set_name.lower(),
                card_number.lower()
            )

            MTGJSON_CARDS[key] = uuid

            identifiers = card.get("identifiers", {})

            tcgplayer_id = identifiers.get("tcgplayerProductId")

            if tcgplayer_id:
                MTGJSON_TCGPLAYER_IDS[key] = str(tcgplayer_id)

            card_count += 1

    print(f"Loaded {card_count:,} card records.")
    
    SERVER_MESSAGE = "Loading price database..."

    # -----------------------------------------------------
    # Load AllPricesToday
    # -----------------------------------------------------

    print("Loading AllPricesToday.json.gz...")

    with gzip.open(
        ALL_PRICES_FILE,
        "rt",
        encoding="utf-8"
    ) as file:

        all_prices = json.load(file)

    MTGJSON_PRICES.update(
        all_prices.get("data", {})
    )

    print(
        f"Loaded {len(MTGJSON_PRICES):,} price records."
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
    # Get paper pricing
    # -----------------------------------------------------

    paper = price_data.get("paper", {})

    tcgplayer = paper.get("tcgplayer", {})

    retail = tcgplayer.get("retail", {})

    # -----------------------------------------------------
    # Determine printing
    # -----------------------------------------------------

    printing_lower = printing.lower()

    if printing_lower == "foil":

        price_type = "foil"

    else:

        price_type = "normal"

    price_history = retail.get(
        price_type,
        {}
    )

    if not price_history:

        return {
            "success": False,
            "error": (
                f"No MTGJSON {price_type} price "
                "was found for this card."
            )
        }

    # -----------------------------------------------------
    # Get latest available date
    # -----------------------------------------------------

    dates = list(price_history.keys())

    if not dates:

        return {
            "success": False,
            "error": (
                "No dated MTGJSON price was found."
            )
        }

    latest_date = max(dates)

    price = price_history.get(
        latest_date
    )

    if price is None:

        return {
            "success": False,
            "error": (
                "MTGJSON price data was empty."
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