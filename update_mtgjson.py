import hashlib
import os
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

DATA_DIR = BASE_DIR / "Data"

FILES = {
    "AllPricesToday": {
        "filename": "AllPricesToday.json.gz",
        "url": "https://mtgjson.com/api/v5/AllPricesToday.json.gz",
        "sha_url": "https://mtgjson.com/api/v5/AllPricesToday.json.gz.sha256",
    },
    "AllPrintings": {
        "filename": "AllPrintings.json.gz",
        "url": "https://mtgjson.com/api/v5/AllPrintings.json.gz",
        "sha_url": "https://mtgjson.com/api/v5/AllPrintings.json.gz.sha256",
    },
}

DOWNLOAD_TIMEOUT = 60


# ============================================================
# Utility functions
# ============================================================

def print_header(text):
    print()
    print("=" * 56)
    print(text)
    print("=" * 56)


def get_remote_sha256(url):
    """
    Download the tiny MTGJSON SHA-256 file and return
    the expected hash.
    """

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Card Pricing Structure MTGJSON Updater"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=DOWNLOAD_TIMEOUT
    ) as response:

        content = response.read().decode("utf-8").strip()

    if not content:
        raise RuntimeError("MTGJSON returned an empty SHA-256 file.")

    # MTGJSON normally returns:
    # HASH  filename
    #
    # We only need the first field.
    remote_hash = content.split()[0].lower()

    if len(remote_hash) != 64:
        raise RuntimeError(
            "Invalid SHA-256 value received from MTGJSON."
        )

    return remote_hash


def calculate_sha256(file_path):
    """
    Calculate SHA-256 for a local file.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest().lower()


def download_file(url, destination):
    """
    Download a file to the specified temporary destination.
    """

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Card Pricing Structure MTGJSON Updater"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=DOWNLOAD_TIMEOUT
    ) as response:

        with open(destination, "wb") as output:

            while True:
                chunk = response.read(1024 * 1024)

                if not chunk:
                    break

                output.write(chunk)


def validate_gzip(file_path):
    """
    Verify that the downloaded gzip file can be completely read.

    We do not need to parse the enormous JSON file here because
    the downloaded file is also verified against MTGJSON's
    published SHA-256 hash.
    """

    import gzip

    with gzip.open(file_path, "rb") as f:

        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break


def replace_file(temp_path, destination):
    """
    Atomically replace the existing file.

    The old file remains untouched until the new file has
    successfully downloaded and passed validation.
    """

    os.replace(temp_path, destination)


# ============================================================
# Update logic
# ============================================================

def update_file(name, info):
    destination = DATA_DIR / info["filename"]

    print()
    print(f"Checking {name}...")
    print(f"Local file: {destination}")

    try:
        remote_hash = get_remote_sha256(info["sha_url"])

    except Exception as e:
        print()
        print("Unable to check for an update.")
        print(f"Reason: {e}")

        if destination.exists():
            print("Result: FALLBACK")
            print("Existing local file will be retained.")
            return "FALLBACK"

        print("Result: FAILED")
        print("WARNING: No local copy exists.")
        return "FAILED"

    print(f"Remote SHA-256: {remote_hash}")

    if not destination.exists():
        print("Local file does not exist.")
        print("Download required.")

        return download_and_replace(
            name,
            info,
            destination,
            remote_hash
        )

    try:
        local_hash = calculate_sha256(destination)

    except Exception as e:
        print()
        print("Unable to read the existing local file.")
        print(f"Reason: {e}")
        print("Download required.")

        return download_and_replace(
            name,
            info,
            destination,
            remote_hash
        )

    print(f"Local SHA-256:  {local_hash}")

    if local_hash == remote_hash:
        print("Result: CURRENT")
        print("No download required.")
        return "CURRENT"

    print("Result: UPDATE AVAILABLE")

    return download_and_replace(
        name,
        info,
        destination,
        remote_hash
    )
    # --------------------------------------------------------
    # No local file
    # --------------------------------------------------------

    if not destination.exists():

        print("Local file does not exist.")
        print("Download required.")

        return download_and_replace(
            name,
            info,
            destination,
            remote_hash
        )

    # --------------------------------------------------------
    # Calculate local hash
    # --------------------------------------------------------

    try:

        local_hash = calculate_sha256(destination)

    except Exception as e:

        print()
        print("Unable to read the existing local file.")
        print(f"Reason: {e}")
        print("Download required.")

        return download_and_replace(
            name,
            info,
            destination,
            remote_hash
        )

    print(f"Local SHA-256:  {local_hash}")

    # --------------------------------------------------------
    # Already current
    # --------------------------------------------------------

    if local_hash == remote_hash:

        print("Result: Already current.")
        print("No download required.")

        return True

    # --------------------------------------------------------
    # Update available
    # --------------------------------------------------------

    print("Result: Update available.")

    return download_and_replace(
        name,
        info,
        destination,
        remote_hash
    )


def download_and_replace(name, info, destination, expected_hash):
    temp_path = None

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        fd, temp_name = tempfile.mkstemp(
            prefix=destination.stem + "_",
            suffix=".tmp",
            dir=DATA_DIR
        )

        os.close(fd)
        temp_path = Path(temp_name)

        print()
        print("Downloading temporary file...")
        print(f"Temporary path: {temp_path}")

        download_file(info["url"], temp_path)

        print("Download complete.")

        print("Validating gzip file...")
        validate_gzip(temp_path)
        print("Gzip validation passed.")

        print("Verifying SHA-256...")
        downloaded_hash = calculate_sha256(temp_path)

        print(f"Downloaded SHA-256: {downloaded_hash}")

        if downloaded_hash != expected_hash:
            raise RuntimeError("SHA-256 verification failed.")

        print("SHA-256 verification passed.")

        print("Replacing existing file...")
        replace_file(temp_path, destination)

        temp_path = None

        print(f"{name} updated successfully.")
        print("Result: UPDATED")

        return "UPDATED"

    except urllib.error.URLError as e:

        print()
        print(f"{name} download failed.")
        print(f"Reason: {e}")

        if destination.exists():
            print("Result: FALLBACK")
            print("Existing known-good file was retained.")
            return "FALLBACK"

        print("Result: FAILED")
        return "FAILED"

    except Exception as e:

        print()
        print(f"{name} update failed.")
        print(f"Reason: {e}")

        if destination.exists():
            print("Result: FALLBACK")
            print("Existing known-good file was retained.")
            return "FALLBACK"

        print("Result: FAILED")
        return "FAILED"

    finally:

        if temp_path is not None and temp_path.exists():

            try:
                temp_path.unlink()

            except Exception:
                pass


# ============================================================
# Main
# ============================================================

def main():
    print_header("MTGJSON Update Check")

    print()
    print("Project directory:")
    print(BASE_DIR)

    print()
    print("Data directory:")
    print(DATA_DIR)

    print()
    print("This updater will:")
    print("  - Check MTGJSON's published SHA-256")
    print("  - Download only changed files")
    print("  - Validate downloads")
    print("  - Verify SHA-256")
    print("  - Replace files only after validation")
    print("  - Retain existing files if an update fails")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    results["AllPricesToday"] = update_file(
        "AllPricesToday",
        FILES["AllPricesToday"]
    )

    results["AllPrintings"] = update_file(
        "AllPrintings",
        FILES["AllPrintings"]
    )

    print_header("Update Check Complete")

    print()

    for name, result in results.items():
        print(f"{name}: {result}")

    print()

    failed = [
        name
        for name, result in results.items()
        if result == "FAILED"
    ]

    fallback = [
        name
        for name, result in results.items()
        if result == "FALLBACK"
    ]

    updated = [
        name
        for name, result in results.items()
        if result == "UPDATED"
    ]

    current = [
        name
        for name, result in results.items()
        if result == "CURRENT"
    ]

    if failed:
        print("Overall result: FAILED")
        print()
        print("One or more databases are unavailable.")
        return 1

    if fallback:
        print("Overall result: FALLBACK")
        print()
        print("One or more updates failed.")
        print("Existing cached databases were retained.")
        return 0

    if updated:
        print("Overall result: UPDATED")
        print()
        print("One or more MTGJSON databases were updated.")
        return 0

    if current:
        print("Overall result: CURRENT")
        print()
        print("All MTGJSON databases are already current.")
        return 0

    print("Overall result: UNKNOWN")
    return 1


if __name__ == "__main__":
    sys.exit(main())
