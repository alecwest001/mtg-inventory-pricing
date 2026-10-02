import json
import urllib.request
import urllib.error

SERVER_BASE = "http://127.0.0.1:5000"

MTGJSON_ENDPOINT = SERVER_BASE + "/get-mtgjson-price"
JUSTTCG_ENDPOINT = SERVER_BASE + "/get-price"


tests = [
    {
        "name": "Counterspell",
        "set": "Commander Masters",
        "number": "81",
        "condition": "NM",
        "printing": "Normal",
        "language": "English",
    },
    {
        "name": "Sol Ring",
        "set": "Commander Masters",
        "number": "703",
        "condition": "NM",
        "printing": "Normal",
        "language": "English",
    },
    {
        "name": "Rhystic Study",
        "set": "Prophecy",
        "number": "45",
        "condition": "NM",
        "printing": "Normal",
        "language": "English",
    },
    {
        "name": "Rhystic Study",
        "set": "Wilds of Eldraine: Enchanting Tales",
        "number": "71",
        "condition": "NM",
        "printing": "Normal",
        "language": "English",
    },
]


CONDITION_MAP = {
    "nm": "near mint",
    "lp": "lightly played",
    "mp": "moderately played",
    "hp": "heavily played",
    "d": "damaged",
}


def post_request(url, data):
    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        print(
            f"HTTP ERROR {error.code}: "
            f"{error.read().decode('utf-8')}"
        )

        return None

    except Exception as error:

        print(
            f"REQUEST ERROR: {error}"
        )

        return None


def run_test(card):
    print("")
    print("=" * 70)
    print(
        f"{card['name']} | "
        f"{card['set']} | "
        f"#{card['number']}"
    )
    print("=" * 70)

    # -----------------------------------------------------
    # Cached MTGJSON
    # -----------------------------------------------------

    mtgjson = post_request(
        MTGJSON_ENDPOINT,
        {
            "cardName": card["name"],
            "set": card["set"],
            "cardNumber": card["number"],
            "printing": card["printing"]
        }
    )

    print("")
    print("CACHED MTGJSON")
    print("-" * 70)

    if not mtgjson:
        print("Request failed.")
        return False

    print(
        f"Success:        "
        f"{mtgjson.get('success')}"
    )

    print(
        f"UUID:           "
        f"{mtgjson.get('uuid')}"
    )

    print(
        f"TCGplayer ID:   "
        f"{mtgjson.get('tcgplayerId')}"
    )

    print(
        f"Price:          "
        f"${mtgjson.get('price')}"
    )

    print(
        f"Price Date:     "
        f"{mtgjson.get('date')}"
    )

    if not mtgjson.get("success"):
        print(
            f"Error:          "
            f"{mtgjson.get('error')}"
        )

        return False

    # -----------------------------------------------------
    # Live JustTCG
    # -----------------------------------------------------

    justtcg = post_request(
        JUSTTCG_ENDPOINT,
        {
            "cardName": card["name"],
            "set": card["set"],
            "cardNumber": card["number"],
            "condition": card["condition"],
            "printing": card["printing"],
            "language": card["language"]
        }
    )

    print("")
    print("LIVE JUSTTCG")
    print("-" * 70)

    if not justtcg:
        print("Request failed.")
        return False

    print(
        f"Success:        "
        f"{justtcg.get('success')}"
    )

    print(
        f"UUID:           "
        f"{justtcg.get('uuid')}"
    )

    print(
        f"TCGplayer ID:   "
        f"{justtcg.get('tcgplayerId')}"
    )

    print(
        f"Live Price:     "
        f"${justtcg.get('price')}"
    )

    print(
        f"Price Date:     "
        f"{justtcg.get('date')}"
    )

    print(
        f"Condition:      "
        f"{justtcg.get('condition')}"
    )

    print(
        f"Printing:       "
        f"{justtcg.get('printing')}"
    )

    print(
        f"Language:        "
        f"{justtcg.get('language')}"
    )

    print(
        f"JustTCG Name:   "
        f"{justtcg.get('justtcgName')}"
    )

    print(
        f"JustTCG Set:    "
        f"{justtcg.get('justtcgSet')}"
    )

    print(
        f"JustTCG Number: "
        f"{justtcg.get('justtcgNumber')}"
    )

    if not justtcg.get("success"):
        print(
            f"Error:          "
            f"{justtcg.get('error')}"
        )

        return False

    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    expected_condition = CONDITION_MAP.get(
        card["condition"].lower(),
        card["condition"].lower()
    )

    uuid_match = (
        mtgjson.get("uuid")
        == justtcg.get("uuid")
    )

    tcgplayer_match = (
        str(mtgjson.get("tcgplayerId"))
        == str(justtcg.get("tcgplayerId"))
    )

    number_match = (
        str(justtcg.get("justtcgNumber", ""))
        == str(card["number"])
    )

    condition_match = (
        justtcg.get("condition", "").lower()
        == expected_condition
    )

    printing_match = (
        justtcg.get("printing", "").lower()
        == card["printing"].lower()
    )

    language_match = (
        justtcg.get("language", "").lower()
        == card["language"].lower()
    )

    print("")
    print("VALIDATION")
    print("-" * 70)

    print(
        f"MTGJSON UUID ↔ JustTCG UUID: "
        f"{'PASS' if uuid_match else 'FAIL'}"
    )

    print(
        f"TCGplayer ID match:           "
        f"{'PASS' if tcgplayer_match else 'FAIL'}"
    )

    print(
        f"Card number match:            "
        f"{'PASS' if number_match else 'FAIL'}"
    )

    print(
        f"Condition match:              "
        f"{'PASS' if condition_match else 'FAIL'}"
    )

    print(
        f"Printing match:               "
        f"{'PASS' if printing_match else 'FAIL'}"
    )

    print(
        f"Language match:               "
        f"{'PASS' if language_match else 'FAIL'}"
    )

    return (
        uuid_match
        and tcgplayer_match
        and number_match
        and condition_match
        and printing_match
        and language_match
    )


# ---------------------------------------------------------
# Run all tests
# ---------------------------------------------------------

print("----------------------------------------")
print("MTG Pricing Integration Test")
print("----------------------------------------")
print(
    f"Server: {SERVER_BASE}"
)

passed = 0

for card in tests:

    if run_test(card):
        passed += 1


print("")
print("=" * 70)
print(
    f"FINAL RESULT: "
    f"{passed}/{len(tests)} cards passed"
)
print("=" * 70)