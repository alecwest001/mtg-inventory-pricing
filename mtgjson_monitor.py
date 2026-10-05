import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import json
from pathlib import Path

# Winotify notifier instance
development_notifier = None

# ============================================================
# Configuration
# ============================================================

BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

DATA_DIR = BASE_DIR / "Data"

UPDATER_EXE = BASE_DIR / "MTGJSONUpdater.exe"
PRICE_SERVER_EXE = BASE_DIR / "PriceServer.exe"

PRICE_SERVER_URL = "http://127.0.0.1:5000"

CHECK_INTERVAL = 60 * 60 * 4

REMINDER_INTERVAL = 60 * 60

TEST_MODE = False

NOTIFICATION_STATE_FILE = (
    DATA_DIR / "MTGJSONNotificationState.json"
)

REQUEST_TIMEOUT = 10

PROTOCOL_SCHEME = "mtgjson-monitor"

FILES = {
    "AllPricesToday": {
        "filename": "AllPricesToday.json.gz",
        "sha_url": (
            "https://mtgjson.com/api/v5/"
            "AllPricesToday.json.gz.sha256"
        ),
    },
    "AllPrintings": {
        "filename": "AllPrintings.json.gz",
        "sha_url": (
            "https://mtgjson.com/api/v5/"
            "AllPrintings.json.gz.sha256"
        ),
    },
}


# ============================================================
# Logging
# ============================================================

def log(message):
    """
    Write monitor activity to stdout.

    The compiled EXE will normally run with console=False,
    so this is primarily useful during development/testing.
    """

    print(
        f"[MTGJSON Monitor] {message}",
        flush=True
    )


# ============================================================
# Windows Protocol Registration
# ============================================================

def register_protocol_handler():
    """
    Register the mtgjson-monitor:// Windows URI protocol
    for the current Windows user.

    Development:
        python.exe mtgjson_monitor.py "%1"

    Production:
        MTGJSONMonitor.exe "%1"

    The URI itself is validated by handle_protocol_callback().
    """

    try:

        if getattr(sys, "frozen", False):

            executable = Path(
                sys.executable
            ).resolve()

            command = (
                f'"{executable}" "%1"'
            )

        else:

            python_executable = Path(
                sys.executable
            ).resolve()

            script_path = Path(
                __file__
            ).resolve()

            command = (
                f'"{python_executable}" '
                f'"{script_path}" "%1"'
            )

        protocol_key_path = (
            rf"HKCU\Software\Classes\{PROTOCOL_SCHEME}"
        )

        command_key_path = (
            rf"{protocol_key_path}\shell\open\command"
        )

        # ----------------------------------------------------
        # Register protocol using reg.exe.
        #
        # Using reg.exe here ensures Windows receives the
        # command string exactly as constructed, including
        # quotes around paths containing spaces.
        # ----------------------------------------------------

        subprocess.run(
            [
                "reg.exe",
                "ADD",
                protocol_key_path,
                "/ve",
                "/d",
                "URL:MTGJSON Monitor Protocol",
                "/f"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        subprocess.run(
            [
                "reg.exe",
                "ADD",
                protocol_key_path,
                "/v",
                "URL Protocol",
                "/t",
                "REG_SZ",
                "/d",
                "",
                "/f"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        subprocess.run(
            [
                "reg.exe",
                "ADD",
                command_key_path,
                "/ve",
                "/d",
                command,
                "/f"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        log(
            f"Protocol command: {command}"
        )

        log(
            "Windows URI protocol registered."
        )

        log(
            f"Protocol: {PROTOCOL_SCHEME}://"
        )

        return True

    except Exception as error:

        log(
            f"Unable to register Windows URI protocol: "
            f"{error}"
        )

        return False


# ============================================================
# URI Callback Handling
# ============================================================

def handle_protocol_callback(callback_url):
    """
    Validate and process an mtgjson-monitor:// callback.

    Only these exact actions are accepted:

        mtgjson-monitor://update
        mtgjson-monitor://later

    No commands, paths, query strings, or arbitrary arguments
    are accepted from the URI.
    """

    if not isinstance(callback_url, str):
        return False

    try:

        parsed = urllib.parse.urlparse(
            callback_url
        )

    except Exception as error:

        log(
            f"Unable to parse protocol callback: "
            f"{error}"
        )

        return False

    if parsed.scheme.lower() != PROTOCOL_SCHEME:
        return False

    if parsed.netloc.lower() not in {
        "update",
        "later",
    }:
        log(
            "Rejected protocol callback: "
            "unknown action."
        )

        return False

    if parsed.path not in ("", "/"):

        log(
            "Rejected protocol callback: "
            "unexpected path."
        )

        return False

    if parsed.query or parsed.fragment:

        log(
            "Rejected protocol callback: "
            "query strings and fragments are not allowed."
        )

        return False

    action = parsed.netloc.lower()

    if action == "update":

        log(
            "Update Now callback received."
        )

        success = perform_update()

        if success:
            log("Update Now callback completed successfully.")
        else:
            log("Update Now callback failed.")

        return True

    if action == "later":

        set_last_notification_time(
            time.time()
        )

        log(
            "Later callback received. "
            "Update notification deferred."
        )

        return True

    return False


# ============================================================
# MTGJSON
# ============================================================

def get_remote_sha256(url):
    """
    Retrieve the current MTGJSON SHA-256 value.
    """

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Card Pricing Structure "
                "MTGJSON Monitor"
            )
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT
    ) as response:

        content = response.read().decode(
            "utf-8"
        ).strip()

    if not content:
        raise RuntimeError(
            "MTGJSON returned an empty SHA-256 file."
        )

    remote_hash = content.split()[0].lower()

    if (
        len(remote_hash) != 64
        or any(
            character not in "0123456789abcdef"
            for character in remote_hash
        )
    ):
        raise RuntimeError(
            "MTGJSON returned an invalid SHA-256 value."
        )

    return remote_hash


def calculate_sha256(file_path):
    """
    Calculate the SHA-256 hash of a local database.
    """

    import hashlib

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:

            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest().lower()


def check_for_updates():
    """
    Compare the local MTGJSON database files against the
    hashes currently published by MTGJSON.

    Returns:

        (update_available, current_hashes)

        update_available:
            True if any local database differs from the
            corresponding remote MTGJSON database.

        current_hashes:
            The remote hashes retrieved during this check.

        (None, current_hashes):
            If the remote check could not be completed.
    """

    log("Checking MTGJSON for updates...")

    current_hashes = {}
    update_available = False
    check_failed = False

    for name, info in FILES.items():

        # ----------------------------------------------------
        # Get current remote hash
        # ----------------------------------------------------

        try:

            remote_hash = get_remote_sha256(
                info["sha_url"]
            )

        except Exception as error:

            log(
                f"Unable to check {name}: "
                f"{error}"
            )

            check_failed = True
            continue

        current_hashes[name] = remote_hash

        log(
            f"{name} remote SHA-256: "
            f"{remote_hash}"
        )

        # ----------------------------------------------------
        # Locate local database
        # ----------------------------------------------------

        local_path = (
            DATA_DIR / info["filename"]
        )

        if not local_path.exists():

            log(
                f"{name}: Local database file "
                f"was not found."
            )

            update_available = True
            continue

        # ----------------------------------------------------
        # Calculate local hash
        # ----------------------------------------------------

        try:

            local_hash = calculate_sha256(
                local_path
            )

        except Exception as error:

            log(
                f"{name}: Unable to calculate "
                f"local SHA-256: {error}"
            )

            check_failed = True
            continue

        log(
            f"{name} local SHA-256: "
            f"{local_hash}"
        )

        # ----------------------------------------------------
        # Compare local database against MTGJSON
        # ----------------------------------------------------

        if remote_hash != local_hash:

            log(
                f"{name}: UPDATE AVAILABLE"
            )

            update_available = True

        else:

            log(
                f"{name}: CURRENT"
            )

    if check_failed:

        return None, current_hashes

    return update_available, current_hashes

# ============================================================
# Price Server
# ============================================================

def get_server_health():
    """
    Check the current PriceServer health.
    """

    try:

        with urllib.request.urlopen(
            PRICE_SERVER_URL + "/health",
            timeout=REQUEST_TIMEOUT
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

        return json.loads(body)

    except Exception:

        return None


def is_server_ready():
    """
    Return True when PriceServer reports ready.
    """

    health = get_server_health()

    if not health:
        return False

    return (
        health.get("status") == "ready"
    )


def wait_for_server(timeout=60):
    """
    Wait for PriceServer to become ready.
    """

    start_time = time.time()

    while (
        time.time() - start_time
        < timeout
    ):

        if is_server_ready():

            log(
                "PriceServer is ready."
            )

            return True

        time.sleep(1)

    log(
        "PriceServer did not become ready "
        "within the expected time."
    )

    return False


def shutdown_price_server():
    """
    Request a clean shutdown from PriceServer.
    """

    log(
        "Requesting PriceServer shutdown..."
    )

    request = urllib.request.Request(
        PRICE_SERVER_URL + "/shutdown",
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            response.read()

        return True

    except Exception as error:

        log(
            f"Unable to request server shutdown: "
            f"{error}"
        )

        return False


def wait_for_server_shutdown(timeout=30):
    """
    Wait until the PriceServer is no longer responding.
    """

    start_time = time.time()

    while (
        time.time() - start_time
        < timeout
    ):

        if get_server_health() is None:

            log(
                "PriceServer has stopped."
            )

            return True

        time.sleep(1)

    log(
        "PriceServer did not shut down "
        "within the expected time."
    )

    return False


def start_price_server():
    """
    Start PriceServer.

    During development, run price_server.py directly.
    In the compiled monitor EXE, run PriceServer.exe.
    """

    if getattr(sys, "frozen", False):

        if not PRICE_SERVER_EXE.exists():

            raise RuntimeError(
                "PriceServer.exe was not found at: "
                f"{PRICE_SERVER_EXE}"
            )

        command = [
            str(PRICE_SERVER_EXE)
        ]

    else:

        price_server_script = (
            BASE_DIR / "price_server.py"
        )

        if not price_server_script.exists():

            raise RuntimeError(
                "price_server.py was not found at: "
                f"{price_server_script}"
            )

        command = [
            sys.executable,
            str(price_server_script)
        ]

    log(
        "Starting PriceServer..."
    )

    if getattr(sys, "frozen", False):

        subprocess.Popen(
            command,
            cwd=str(BASE_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    else:

        subprocess.Popen(
            command,
            cwd=str(BASE_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    return wait_for_server()


def restart_price_server():
    """
    Cleanly restart PriceServer.
    """

    log(
        "Restarting PriceServer..."
    )

    if is_server_ready():

        if not shutdown_price_server():

            return False

        if not wait_for_server_shutdown():

            return False

    else:

        log(
            "PriceServer is not currently ready."
        )

    return start_price_server()


# ============================================================
# MTGJSON Updater
# ============================================================

def run_updater():
    """
    Run the MTGJSON updater.

    During development, run update_mtgjson.py directly.
    In the compiled monitor EXE, run MTGJSONUpdater.exe.
    """

    if getattr(sys, "frozen", False):

        if not UPDATER_EXE.exists():

            log(
                "MTGJSONUpdater.exe was not found at: "
                f"{UPDATER_EXE}"
            )

            return 1

        command = [
            str(UPDATER_EXE)
        ]

    else:

        updater_script = (
            BASE_DIR / "update_mtgjson.py"
        )

        if not updater_script.exists():

            log(
                "update_mtgjson.py was not found."
            )

            return 1

        command = [
            sys.executable,
            str(updater_script)
        ]

    log(
        "Starting MTGJSON updater..."
    )

    result = subprocess.run(
        command,
        cwd=str(BASE_DIR)
    )

    log(
        f"MTGJSON updater exited with code "
        f"{result.returncode}."
    )

    return result.returncode


def get_update_result():
    """
    Read the result written by MTGJSONUpdater.
    """

    result_path = (
        DATA_DIR / "MTGJSONUpdateResult.json"
    )

    if not result_path.exists():

        log(
            "MTGJSON update result file was not found."
        )

        return None

    try:

        with open(
            result_path,
            "r",
            encoding="utf-8"
        ) as file:

            result = json.load(file)

    except Exception as error:

        log(
            f"Unable to read MTGJSON update result: "
            f"{error}"
        )

        return None

    overall_result = result.get(
        "overall_result"
    )

    log(
        f"MTGJSON updater result: "
        f"{overall_result}"
    )

    return overall_result


# ============================================================
# Notification State
# ============================================================

def get_last_notification_time():
    """
    Read the time the last update notification was shown
    or deferred.
    """

    if not NOTIFICATION_STATE_FILE.exists():
        return None

    try:

        with open(
            NOTIFICATION_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            state = json.load(file)

        value = state.get(
            "last_notification_time"
        )

        if isinstance(value, (int, float)):
            return value

    except Exception as error:

        log(
            f"Unable to read notification state: "
            f"{error}"
        )

    return None


def set_last_notification_time(timestamp):
    """
    Store the time the update notification was last shown
    or deferred.
    """

    try:
        if timestamp is None:

            if NOTIFICATION_STATE_FILE.exists():

                NOTIFICATION_STATE_FILE.unlink()

            return

        with open(
            NOTIFICATION_STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "last_notification_time": timestamp
                },
                file
            )

    except Exception as error:

        log(
            f"Unable to save notification state: "
            f"{error}"
        )


# ============================================================
# Notification
# ============================================================

def show_update_notification():
    """
    Show the MTGJSON update notification.

    Notifications are limited by REMINDER_INTERVAL so that
    choosing Later does not result in a notification every
    monitor check.
    """
    if not TEST_MODE:

        last_notification = get_last_notification_time()

        if last_notification is not None:

            elapsed = (
                time.time() - last_notification
            )

            if elapsed < REMINDER_INTERVAL:

                log(
                    "Update notification is currently "
                    "within the reminder interval."
                )

                return False

    result = show_notification()

    if result:

        set_last_notification_time(
            time.time()
        )

    return result


def initialize_notifier():
    """
    Initialize a single Winotify notifier for the lifetime
    of the monitor process.
    """

    global development_notifier

    if development_notifier is not None:
        return development_notifier

    import winotify

    registry = winotify.Registry(
        "MTGJSON Toast",
        winotify.PY_EXE,
        str(Path(__file__).resolve())
    )

    development_notifier = winotify.Notifier(
        registry
    )

    return development_notifier


def show_notification():
    """
    Display the update notification.

    The buttons use the registered Windows URI protocol.
    """

    notifier = initialize_notifier()

    log(
        "Showing MTGJSON update notification."
    )

    toast = notifier.create_notification(
        title="MTGJSON Update Available",
        msg=(
            "A new MTGJSON database version is available."
        )
    )

    toast.add_actions(
        label="Update Now",
        launch="mtgjson-monitor://update"
    )

    toast.add_actions(
        label="Later",
        launch="mtgjson-monitor://later"
    )

    toast.show()

    return True


# ============================================================
# Update Workflow
# ============================================================

def perform_update():
    """
    Run the complete MTGJSON update/restart workflow.
    """

    log(
        "Beginning MTGJSON update."
    )

    exit_code = run_updater()

    if exit_code != 0:

        log(
            "MTGJSON updater reported failure."
        )

        return False

    overall_result = get_update_result()

    if overall_result is None:

        log(
            "Unable to determine MTGJSON update result."
        )

        return False

    if overall_result == "UPDATED":

        log(
            "MTGJSON databases were updated."
        )

        if not restart_price_server():

            log(
                "PriceServer restart failed."
            )

            return False

        set_last_notification_time(
            None
        )

        log(
            "MTGJSON update and PriceServer "
            "restart completed successfully."
        )

        return True

    if overall_result == "CURRENT":

        log(
            "MTGJSON databases were already current."
        )

        return True

    if overall_result == "FALLBACK":

        log(
            "MTGJSON updater used fallback data. "
            "PriceServer will not be restarted."
        )

        return False

    if overall_result == "FAILED":

        log(
            "MTGJSON update failed. "
            "PriceServer will not be restarted."
        )

        return False

    log(
        f"Unknown MTGJSON update result: "
        f"{overall_result}"
    )

    return False


# ============================================================
# Main Monitor
# ============================================================

def main():

    log(
        "MTGJSON background monitor started."
    )

    log(
        f"Check interval: "
        f"{CHECK_INTERVAL} seconds"
    )

    register_protocol_handler()

    while True:

        try:

            update_available, _ = (
                check_for_updates()
            )

            if update_available:

                log(
                    "An MTGJSON update is available."
                )

                show_update_notification()

            elif update_available is False:

                log(
                    "MTGJSON databases are current."
                )

            else:

                log(
                    "MTGJSON update check failed."
                )

        except Exception as error:

            log(
                f"Unexpected monitor error: "
                f"{error}"
            )

        log(
            "Sleeping until next check..."
        )

        sleep_remaining = CHECK_INTERVAL

        while sleep_remaining > 0:

            time.sleep(0.25)

            sleep_remaining -= 0.25


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) > 1:

        callback_url = sys.argv[1]

        if handle_protocol_callback(
            callback_url
        ):

            sys.exit(0)

    main()