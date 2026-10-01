import gzip
import json
import urllib.request


MTGJSON_FILE = "Data/AllPrintings.json.gz"
SERVER_URL = "http://127.0.0.1:5000/get-price"


TEST_CARDS = [
    {
        "name": "  Counterspell  ",
        "set": "Commander   Masters",
        "number": "81"
    },
    {
        "name": "Sol   Ring",
        "set": " commander masters ",
        "number": "703"
    },
    {
        "name": "RHYSTIC STUDY",
        "set": "Prophecy",
        "number": "45"
    },
    {
        "name": "Rhystic   Study",
        "set": "Wilds of Eldraine: Enchanting Tales",
        "number": "71"
    }
]


def normalize(text):
    return " ".join(
        str(text).strip().lower().split()
    )


def normalize_set(text):
    return normalize(
        text.replace("-", " ")
    )


def load_mtgjson():
    print("Loading MTGJSON...")

    with gzip.open(
        MTGJSON_FILE,
        "rt",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def find_card(data, name, set_name, number):

    normalized_name = normalize(name)
    normalized_set_name = normalize_set(set_name)
    normalized_number = str(number).strip()

    for set_code, mtg_set in data["data"].items():

        actual_set_name = mtg_set.get(
            "name",
            ""
        )

        if normalize_set(actual_set_name) != normalized_set_name:
            continue

        for card in mtg_set.get("cards", []):

            if (
                normalize(card.get("name", ""))
                == normalized_name
                and
                str(card.get("number", "")).strip()
                == normalized_number
            ):
                return card

    return None


def lookup_justtcg(card_name, set_name, number):

    set_id = normalize_set(set_name)
    set_id = set_id.replace(" ", "-")
    set_id += "-magic-the-gathering"

    request_data = {
        "cardName": card_name.strip(),
        "setID": set_id,
        "cardNumber": str(number).strip(),
        "condition": "Near Mint",
        "printing": "Normal",
        "language": "English"
    }

    body = json.dumps(
        request_data
    ).encode("utf-8")

    request = urllib.request.Request(
        SERVER_URL,
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def main():

    data = load_mtgjson()

    for test in TEST_CARDS:

        print()
        print("=" * 70)
        print(
            f'{test["name"]} | '
            f'{test["set"]} | '
            f'#{test["number"]}'
        )
        print("=" * 70)

        card = find_card(
            data,
            test["name"],
            test["set"],
            test["number"]
        )

        if card is None:

            print()
            print("MTGJSON: NOT FOUND")
            continue

        print()
        print("MTGJSON:")
        print(
            f'  Name: {card.get("name")}'
        )
        print(
            f'  Set: {card.get("setName")}'
        )
        print(
            f'  Number: {card.get("number")}'
        )
        print(
            f'  UUID: {card.get("uuid")}'
        )
        print(
            "  TCGplayer Product ID: "
            f'{card.get("identifiers", {}).get("tcgplayerProductId")}'
        )

        result = lookup_justtcg(
            test["name"],
            test["set"],
            test["number"]
        )

        print()
        print("JustTCG:")

        if not result.get("success"):

            print(
                "  ERROR:",
                result.get("error")
            )
            continue

        print(
            f'  Card: {result.get("card_name")}'
        )
        print(
            f'  Set: {result.get("set_name")}'
        )
        print(
            f'  Number: {result.get("card_number")}'
        )
        print(
            f'  MTGJSON ID: {result.get("mtgjsonId")}'
        )
        print(
            "  TCGplayer Product ID: "
            f'{result.get("tcgplayerId")}'
        )
        print(
            f'  Price: {result.get("price")}'
        )

        mtgjson_tcg_id = (
            card.get("identifiers", {})
            .get("tcgplayerProductId")
        )

        justtcg_tcg_id = result.get(
            "tcgplayerId"
        )

        print()
        print("RESULT:")

        if str(mtgjson_tcg_id) == str(
            justtcg_tcg_id
        ):
            print(
                "  TCGplayer ID: MATCH"
            )
        else:
            print(
                "  TCGplayer ID: NO MATCH"
            )


if __name__ == "__main__":
    main()