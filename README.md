# Internet Connection Monitor with WiFi Auto-Switch

A robust Python tool that monitors internet connectivity and automatically switches between WiFi networks when connection is lost. Sends real-time notifications via Telegram bot.

## Features

✅ **Continuous Internet Monitoring** - Pings NTP server every 5 minutes  
✅ **Automatic WiFi Switching** - Tries up to 3 WiFi networks in priority order  
✅ **Intelligent Ping Logic** - 10 consecutive pings per check with early exit at 5 failures  
✅ **Message Queuing** - Queues notifications when offline, sends them when connection restored  
✅ **Telegram Notifications** - Real-time alerts to multiple chat groups  
✅ **Telegram Commands** - `/wifistatus`, `/help`, `/start` for remote status checks  
✅ **Systemd Integration** - Run as Linux background service  
✅ **Cross-Platform** - Windows (netsh) and Linux (nmcli) support  

## Configuration

### 1. WiFi Networks

Edit the WiFi configuration in `netchange.py`:

```python
PRIMARY_WIFI = "PRIMARY_WIFI_NAME"      # Priority 1 - Preferred
SECONDARY_WIFI = "SECONDARY_WIFI_NAME"  # Priority 2 - Fallback
FALLBACK_WIFI = "FALLBACK_WIFI_NAME"    # Priority 3 - Last resort
```

The tool tries them in this order when connection is lost.

### 2. Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Create or get your chat group IDs
4. Update configuration:

```python
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_IDS = [
    # "YOUR_CHAT_ID_1",
    # "YOUR_CHAT_ID_2",
    # "YOUR_CHAT_ID_3",
]
```

### 3. Timing Configuration

```python
PING_INTERVAL = 300              # Check interval: 5 minutes
PING_TIMEOUT = 5                 # Ping timeout: 5 seconds each
RETRY_PRIMARY_INTERVAL = 3600*3  # Retry primary WiFi: every 3 hours
```

## Installation

### Requirements
- Python 3.6+
- `requests` library
- Linux: `nmcli` (NetworkManager)
- Windows: `netsh` (built-in)

### Install Dependencies

```bash
pip install requests
```

### Copy the file in the /opt/netchange

Create folder in the /opt folder named netchange

```bash
sudo mkdir /opt/netchange
``` 

### Linux Systemd Service Setup

Create `/etc/systemd/system/netchange.service`:

```ini
[Unit]
Description=Internet Connection Monitor with WiFi Auto-Switch
After=network.target

[Service]
Type=simple
User="your username"
WorkingDirectory=/opt/netchange
ExecStart=/usr/bin/python3 -u /opt/netchange/netchange.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="PYTHONUNBUFFERED=1" # This will show all the journalctl instead of the general status

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable netchange
sudo systemctl start netchange

# View logs
journalctl -u netchange -f
```

## How It Works

### Monitoring Cycle (Every 5 minutes)

1. **Internet Check**: Pings NTP server 10 times
   - Success: 0-4 failures → Connection is good
   - Failure: 5+ failures → Connection is lost

2. **If Connected**:
   - Log status
   - Every 3 hours: Try to switch back to PRIMARY WiFi
   - If successful: Send notification + flush queued messages

3. **If Disconnected**:
   - Send alert notification
   - Try WiFi networks in priority order:
     1. PRIMARY_WIFI 
     2. SECONDARY_WIFI 
     3. FALLBACK_WIFI 
   - First one with internet wins
   - Send success notification + flush queued messages

### Message Queue System

When internet is lost:
- Failed Telegram messages are queued with timestamp
- Queue stored in memory (`pending_messages` list)
- When connection restored → all queued messages sent immediately
- Prevents notification loss during WiFi transitions

## Telegram Commands

Send these commands to the bot in a direct chat or group:

| Command | Response |
|---------|----------|
| `/start` | Show available commands |
| `/help` | Show help message |
| `/wifistatus` | Check internet and WiFi connection status |

Works in both direct and group chats (format: `/command@botname`)

## Usage

### Run Directly

```bash
python3 netchange.py
```

### Run as Systemd Service

```bash
sudo systemctl start netchange    # Start service
sudo systemctl stop netchange     # Stop service
sudo systemctl restart netchange  # Restart service
journalctl -u netchange -f        # View live logs
```

## Log Output Example

```
============================================================
Internet Connection Monitor
Monitoring: pool.ntp.org
Primary WiFi: wifi 1
Secondary WiFi: wifi 2
Fallback WiFi: wifi 3
Ping Interval: 300 seconds
Retry Primary Every: 3 hours
Ping Strategy: 10 consecutive pings per check
WiFi Switch Trigger: 5 or more failed pings (out of 10)
============================================================

[2025-12-29 14:30:45] ✓ Connected (WiFi: wifi 1)
[2025-12-29 14:35:45] ⚠ Internet connection lost!
[2025-12-29 14:35:47] → Attempting to connect to wifi 1 (Priority 1)
[2025-12-29 14:35:52] ✗ wifi 1 has no internet, trying next priority
[2025-12-29 14:35:52] → Attempting to connect to wifi 2 (Priority 2)
[2025-12-29 14:35:57] ✓ Connected to wifi 2
[✓] Telegram message sent to -1234567890
[*] Flushing 3 pending message(s)...
[✓] Pending message sent (queue: 2 remaining)
```

## Notification Examples

### Connection Lost
```
⚠️ Internet connection lost!
Time: 2025-12-29 14:35:45
```

### WiFi Switch Success
```
✅ Connected to wifi 2!
Time: 2025-12-29 14:35:57
```

### Connection Restored
```
✅ Internet connection restored!
WiFi: wifi 1
Time: 2025-12-29 14:45:30
```

### WiFi Status Query
```
✅ Connection Status
Internet: Connected
WiFi: wifi 1
Time: 2025-12-29 14:50:15
```

## Architecture

### Threading Model

- **Main Thread**: Monitoring loop (pings every 5 minutes)
- **Daemon Thread**: Telegram listener (long polling, 30-sec timeout)

Both threads handle their own messaging independently.

### Core Functions

| Function | Purpose |
|----------|---------|
| `check_internet_connection()` | 10-ping connectivity check |
| `send_telegram_message()` | Send message to all chat IDs |
| `queue_telegram_message()` | Queue message for later sending |
| `flush_pending_messages()` | Send all queued messages |
| `handle_telegram_commands()` | Listen for Telegram commands |
| `connect_to_wifi()` | Switch WiFi networks |
| `get_current_wifi()` | Get connected network (wlan0 only) |

## Troubleshooting

### Bot not responding to commands

**Problem**: Telegram commands are ignored  
**Solution**: 
- Check bot token is correct
- Ensure bot is in the group chat
- Verify chat IDs are correct and negative for groups
- Check logs: `journalctl -u netchange -f`

### Messages not sent during WiFi switch

**Problem**: Notifications disappear during transitions  
**Solution**: 
- This is now handled by message queue system
- Check that queue is flushing (look for "Flushing N pending" in logs)
- Verify internet connectivity is actually restored

### Service not logging output

**Problem**: Systemd service runs but no logs visible  
**Solution**:
- Add `PYTHONUNBUFFERED=1` to service file
- Use `journalctl -u netchange -f` instead of checking log files
- Ensure service file has `StandardOutput=journal` and `StandardError=journal`

### WiFi not connecting

**Problem**: Tool logs connection attempts but doesn't connect  
**Solution**:
- Verify WiFi SSID names match exactly (case-sensitive)
- Check WiFi signal strength
- On Linux: ensure `nmcli` is installed (`sudo apt install network-manager`)
- On Windows: ensure `netsh` has correct WiFi names

## Performance Notes

- Minimal CPU/memory usage (single-threaded monitoring)
- ~10 seconds per check cycle (10 pings at 5 sec timeout each)
- Network requests use 10-second timeout to prevent hangs
- Early exit at 5 ping failures to reduce check time

## Files

```
netchange/
├── netchange.py      # Main application
├── README.md         # This file
├── SETUP.md          # Additional setup notes
└── netchange.sh      # Optional shell wrapper
```

## License

Free to use and modify.

## Support

For issues or feature requests, check logs and verify configuration matches your WiFi network names and Telegram credentials.
