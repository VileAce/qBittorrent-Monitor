# qBittorrent-Monitor

I kept losing my connection whenever my VPN dropped, and qBittorrent wouldn’t recover until I manually refreshed the network. So I wrote a small background tool that watches the connection status and tells me when something is wrong.

What it does

Polls the WebUI API (/api/v2/transfer/info) and reads connection_status. It alerts on firewalled (“no direct connection”) or disconnected.
Only runs its checks while qbittorrent.exe is running, so it stays quiet if qBittorrent is closed.
Shows a Windows 11 toast notification, plus a popup that stays on screen until you click OK.
Plays an alarm sound (I use C:\Windows\Media\alarm10.wav, but any wav works).
Waits for several bad checks in a row before alerting, so brief blips and the firewalled status right after startup don’t trigger false alarms.
Alerts once per problem and re-arms after the connection returns to connected.
Ignores the case where the WebUI isn’t reachable yet, such as while qBittorrent is still starting.
Prevents duplicate copies from running.
Packages into a single windowless .exe with PyInstaller, so it can start with Windows.

Easy to adjust

The settings are grouped at the top of the script, with comments: check interval, number of failed checks before alerting, sound file (or none), toast duration, and the API address and port.

Requirements

Windows 11, Python 3.x (I used 3.14), and pip install winotify
qBittorrent’s WebUI enabled (I use the “Bypass authentication for clients on localhost” option so no password is needed)
Tested with qBittorrent v5.3.00

Script included, so you can read it and build the exe yourself if you’d rather not run mine.  Some antivirus may flag the .EXE, since unsigned PyInstaller one-file builds often trigger false positives.
