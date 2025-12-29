# Internet Connection Monitor - Setup Guide

## Overview
This Python app monitors your internet connection by pinging pool.ntp.org every 5 minutes. If the connection is lost, it automatically tries to connect to one of three WiFi networks in priority order and sends you Telegram notifications. Lost messages are queued and sent when connection is restored.

## Prerequisites

### Python 3.6+
```bash
python --version
```

### Required Python Packages
```bash
pip install requests
```

### Linux Users (for WiFi auto-connect)
- `nmcli` (usually pre-installed with NetworkManager)
- `sudo` privileges for WiFi connection commands

### Windows Users
- For WiFi auto-connect, run the app with administrator previledge
- Or manually connect to the WiFi network

## Setup Instructions

### 1. Get Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/start`
3. Send `/newbot`
4. Follow the prompts to create a new bot
5. Copy the **Bot Token** (format: `123456789:ABCDefGHijKLmnoPQRstUVwxyz`)
6. Create OS environment variable

```bash
sudo nano /etc/netchange.env
```

7. insert this line:
```ini
TELEGRAM_BOT_TOKEN_NETCHANGE="your bot token, without the quotation marks"
```

update the ownership
```bash
sudo chmod 600 /etc/netchange.env
sudo chown root:root /etc/netchange.env
```

### 2. Get Your Telegram Chat ID

**Option A: Using @userinfobot**
1. Search for **@userinfobot** in Telegram
2. Send `/start`
3. The bot will display your Chat ID

**Option B: Manually**
1. Start a conversation with your new bot
2. Send any message to it
3. Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
4. Look for `"chat"{"id":YOUR_CHAT_ID}`

### 3. Configure the Python Script

Edit `netchange.py` and replace:
```python
PRIMARY_WIFI = "PRIMARY_WIFI_NAME"      # Priority 1 - Preferred
SECONDARY_WIFI = "SECONDARY_WIFI_NAME"  # Priority 2 - Fallback
FALLBACK_WIFI = "FALLBACK_WIFI_NAME"    # Priority 3 - Last resort
TELEGRAM_CHAT_IDS = [
    # "YOUR_CHAT_ID_1",
    # "YOUR_CHAT_ID_2",
    # "YOUR_CHAT_ID_3",D 2
]
```

**Important**: For group chats, use negative group IDs (prefix with `-`)

### 4. (Optional) Configure Timing and WiFi Settings

Edit `netchange.py` to change:
```python
NTP_SERVER = "pool.ntp.org"              # NTP server to ping
PING_INTERVAL = 300                       # Seconds between checks (5 minutes)
PING_TIMEOUT = 5                          # Timeout per ping (seconds)
RETRY_PRIMARY_INTERVAL = 3600 * 3         # Retry primary WiFi every 3 hours
```

## Running the App

### Quick Start (Linux/Mac)
```bash
python3 netchange.py
```

### Running as Systemd Service (Linux)

1. **Create service file:**
```bash
sudo nano /etc/systemd/system/netchange.service
```

2. **Paste this content:**
```ini
[Unit]
Description=Internet Connection Monitor with WiFi Auto-Switch
After=network.target

[Service]
Type=simple
User="your username"
WorkingDirectory=/opt/netchange
Environment="PYTHONUNBUFFERED=1"        # This will show all the journalctl instead of the general status
EnvironmentFile=/etc/netchange.env
ExecStart=/usr/bin/python3 -u /opt/netchange/netchange.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

3. **Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable netchange
sudo systemctl start netchange
```

4. **View logs:**
```bash
journalctl -u netchange -f
```

## Features

✅ **Internet Monitoring** - Pings pool.ntp.org every 5 minutes
✅ **Priority WiFi Switching** - Tries 3 networks in order (Primary → Secondary → Fallback)
✅ **Intelligent Ping Logic** - 10 consecutive pings per check with early exit at 5 failures
✅ **Message Queuing** - Queues notifications when offline, sends when restored
✅ **Telegram Commands** - `/wifistatus`, `/help`, `/start` for remote checks
✅ **Group Chat Support** - Send notifications to multiple group chats
✅ **Systemd Integration** - Run as Linux background service
✅ **Cross-Platform** - Works on Linux, Mac, and Windows

## Notifications You'll Receive

- ✅ **Connected** - Internet restored with current WiFi
- ❌ **Connection Lost** - Internet connectivity failed
- 🔄 **WiFi Switched** - Successfully switched to another network
- 🔃 **Retrying Primary** - Attempting to switch back to primary WiFi
- 📋 **Status Query** - Response to `/wifistatus` command

### Message Queue Behavior

When internet is temporarily lost:
- Telegram notifications that fail to send are **queued with timestamp**
- When internet is restored, **all queued messages are sent immediately**
- Prevents notification loss during WiFi transitions

## Troubleshooting

### Telegram messages not sending
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify `TELEGRAM_CHAT_IDS` list is not empty
- For group chats, ensure IDs are **negative** (e.g., `-1234567890`)
- Check bot is added to the group chat
- Messages are queued if connection fails temporarily

### Bot not responding to commands
- Ensure bot is in the group chat
- Try `/help` or `/start` command
- Check logs: `journalctl -u netchange -f` (systemd) or console output
- Group commands must use format: `/command@botname`

### WiFi connection fails (Linux)
- Ensure `nmcli` is installed: `sudo apt install network-manager`
- Run with sudo if needed: `sudo python3 netchange.py`
- Verify WiFi network names match exactly (case-sensitive)
- Check signal strength: `nmcli device wifi list`

### WiFi connection fails (Windows)
- Verify WiFi network names in configuration are correct
- Check WiFi adapter is enabled
- Use `netsh wlan show networks` to list available networks
- Run as administrator if needed

## Security Note

⚠️ **Store your Bot Token securely!** 

Consider using environment variables instead of hardcoding:
```python
import os
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
```

Then set before running:
```bash
export TG_BOT_TOKEN="your_token_here"
python3 netchange.py
```

Or use a config file that's not in git.

## Telegram Group Chat IDs

To find your group chat ID:
1. Add bot to group
2. Send any message in the group
3. Visit: `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
4. Find `chat.id` (will be negative for groups)

**Example:**
```json
"chat": {
  "id": -1234567890,
  "title": "My Group"
}
```

Use the negative ID in config: `-1234567890`
