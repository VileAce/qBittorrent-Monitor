"""
qBittorrent connection monitor (Windows 11)

Shows a toast notification and a topmost popup, and plays an alarm sound,
when qBittorrent's connection_status is anything other than "connected".
It only checks while qbittorrent.exe is actually running.

SETUP
  1. In qBittorrent: Tools > Options > WebUI, enable "Web User Interface
     (Remote control)" and "Bypass authentication for clients on localhost".
     Make sure the port matches API_URL below (default 8080).
  2. Install the one dependency:   pip install winotify
  3. Test the alert immediately:   python qbit_monitor.py --test
  4. Run it normally:              python qbit_monitor.py
     (use pythonw qbit_monitor.py to run without a console window)

BUILD YOUR OWN .EXE (optional)
  pip install pyinstaller
  pyinstaller --onefile --noconsole --name QbitMonitor qbit_monitor.py
  The exe is created in the dist folder. To start it with Windows, put a
  shortcut to it in the folder opened by pressing Win+R and running shell:startup

TROUBLESHOOTING
  Toast errors are written to qbit_monitor.log next to the script/exe.
"""
import ctypes
import datetime
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import winsound

from winotify import Notification

# =============================================================================
# SETTINGS - change these to adjust behavior
# =============================================================================

# Address of the qBittorrent WebUI API. Change the port if you changed it in
# qBittorrent's WebUI options.
API_URL = "http://localhost:8080/api/v2/transfer/info"

# Name of the qBittorrent process. Checks are skipped while it isn't running.
PROCESS_NAME = "qbittorrent.exe"

# DELAY: seconds to wait between each check.
# 20 is very light on resources. Raise to 60 for once-a-minute checks.
CHECK_INTERVAL = 20

# NUMBER OF CHECKS: how many bad checks in a row are needed before alerting.
# Time until alert is roughly CHECK_INTERVAL x FAILS_BEFORE_ALERT
# (currently 20 x 5 = about 100 seconds). Raise it to tolerate longer VPN
# drops before being alerted; lower it to be alerted sooner.
FAILS_BEFORE_ALERT = 5

# SOUND: wav file played when the alert happens.
# Set to None (no quotes) to disable the sound.
ALARM_SOUND = r"C:\Windows\Media\alarm10.wav"

# TOAST DURATION: how long the Windows toast stays on screen.
# "short" is about 7 seconds, "long" is about 25 seconds.
# (The popup window itself stays until you click OK.)
TOAST_DURATION = "long"

# =============================================================================

LOG_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)),
    "qbit_monitor.log",
)


def log(text: str) -> None:
    """Append a line to qbit_monitor.log (next to the script/exe) for troubleshooting."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {text}\n")
    except Exception:
        pass


CREATE_NO_WINDOW = 0x08000000
MB_ICONWARNING = 0x30
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000


def qbittorrent_running() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {PROCESS_NAME}", "/NH", "/FO", "CSV"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        ).stdout
        return PROCESS_NAME in out.lower()
    except Exception:
        return False


def get_status():
    """Return connection_status string, or None if the WebUI can't be reached."""
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as resp:
            return json.load(resp).get("connection_status")
    except Exception:
        return None


def alert(status: str) -> threading.Thread:
    title = "qBittorrent connection problem"
    if status == "firewalled":
        msg = "Status: firewalled (no direct/incoming connections)."
    elif status == "disconnected":
        msg = "Status: disconnected (no network connection)."
    else:
        msg = f"Status: {status}"

    # Alarm sound (plays in the background so monitoring isn't blocked).
    if ALARM_SOUND:
        try:
            winsound.PlaySound(ALARM_SOUND, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    # Windows toast. It plays Windows' normal short notification chime along
    # with the alarm sound above.
    try:
        toast = Notification(
            app_id="qBittorrent Monitor",
            title=title,
            msg=msg,
            duration=TOAST_DURATION,
        )
        toast.show()
    except Exception as e:
        log(f"Toast failed: {e!r}")

    # Popup stays on screen until OK is clicked. MessageBox blocks, so it runs
    # in its own thread to keep the monitoring loop going.
    t = threading.Thread(
        target=lambda: ctypes.windll.user32.MessageBoxW(
            0, msg, title, MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST
        ),
        daemon=True,
    )
    t.start()
    return t


def single_instance() -> None:
    ctypes.windll.kernel32.CreateMutexW(None, False, "QbitConnectionMonitorMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)


def main() -> None:
    if "--test" in sys.argv:
        # Wait for the popup to be closed so the test doesn't exit early.
        alert("firewalled").join()
        return

    single_instance()

    bad_count = 0
    alerted = False

    while True:
        if not qbittorrent_running():
            bad_count, alerted = 0, False
        else:
            status = get_status()
            if status is None:
                pass  # WebUI not reachable yet (e.g. still starting); don't count it
            elif status == "connected":
                bad_count, alerted = 0, False
            else:
                bad_count += 1
                if bad_count >= FAILS_BEFORE_ALERT and not alerted:
                    alert(status)
                    alerted = True  # one alert per problem episode
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
