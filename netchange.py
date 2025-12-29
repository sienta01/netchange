#!/usr/bin/env python3
"""
netchange
=============================

Internet connection monitor with WiFi auto-connect and Telegram notification.
Pings specified server to check internet connectivity.
If connection is lost, change WiFi and sends Telegram notification.
"""

import subprocess
import time
import requests
from datetime import datetime
import os
import sys
import threading
import json

# ===== CONFIGURATION =====
VERSION = "1.1.1"
NTP_SERVER = "pool.ntp.org"
PRIMARY_WIFI = "PRIMARY_WIFI_NAME"          # Priority 1 - Preferred
SECONDARY_WIFI = "SECONDARY_WIFI_NAME"      # Priority 2 - Fallback
FALLBACK_WIFI = "FALLBACK_WIFI_NAME"        # Priority 3 - Last resort
PING_INTERVAL = 300                         # seconds between ping attempts
PING_TIMEOUT = 5                            # timeout for each ping
RETRY_PRIMARY_INTERVAL = 3600 * 3           # Retry primary WiFi every 3 hours (in seconds)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_NETCHANGE")
TELEGRAM_CHAT_IDS = [
    # "YOUR_CHAT_ID_1",
    # "YOUR_CHAT_ID_2",
    # "YOUR_CHAT_ID_3",
]
TOTAL_PING = 20                             # Total pings per check
MAX_FAILED_PINGS = 10                       # Max failed pings to consider connection lost

# Message queue for pending notifications (store when offline, send when online)
pending_messages = []

# ===== TELEGRAM FUNCTIONS =====
def send_telegram_message(message, skip_queue=False):
    """Send a message via Telegram bot to all configured chat IDs.
    If all sends fail and skip_queue is False, queue the message for later."""
    if not TELEGRAM_BOT_TOKEN:
        print("[WARNING] Telegram bot not configured. Skipping Telegram notification.")
        return False
    
    if not TELEGRAM_CHAT_IDS:
        print("[WARNING] Telegram chat IDs not configured. Skipping Telegram notification.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    sent_count = 0
    failed_count = 0
    
    for chat_id in TELEGRAM_CHAT_IDS:
        if not chat_id:
            continue
        
        try:
            data = {
                "chat_id": chat_id,
                "text": message
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print(f"[✓] Telegram message sent to {chat_id}")
                sent_count += 1
            else:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                print(f"[✗] Failed to send to {chat_id}: {error_msg}")
                failed_count += 1
        except requests.exceptions.Timeout:
            print(f"[✗] Telegram request timeout for {chat_id}")
            failed_count += 1
        except requests.exceptions.ConnectionError as e:
            print(f"[✗] Connection error sending to {chat_id}: {e}")
            failed_count += 1
        except Exception as e:
            print(f"[✗] Error sending Telegram message to {chat_id}: {e}")
            failed_count += 1
    
    if sent_count == 0 and failed_count > 0:
        print(f"[!] Telegram: Failed to send to all {failed_count} chat(s)")
        if not skip_queue:
            queue_telegram_message(message)
    
    return sent_count > 0

def queue_telegram_message(message):
    """Queue a message to be sent when internet is available."""
    global pending_messages
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pending_messages.append({
        "message": message,
        "queued_at": timestamp
    })
    print(f"[*] Message queued (pending: {len(pending_messages)}): {message[:50]}...")

def flush_pending_messages():
    """Send all pending messages in queue."""
    global pending_messages
    if not pending_messages:
        return
    
    print(f"[*] Flushing {len(pending_messages)} pending message(s)...")
    for item in pending_messages[:]:  # Copy list to iterate safely
        if send_telegram_message(item["message"]):
            pending_messages.remove(item)
            print(f"[✓] Pending message sent (queue: {len(pending_messages)} remaining)")
        else:
            print(f"[✗] Failed to send pending message, keeping in queue")
            break  # Stop on first failure, will retry later

def handle_telegram_commands():
    """Listen for Telegram bot commands and respond.
    
    For group chats: Make sure to set bot commands using:
    /setcommands command1 - Description 1
                 command2 - Description 2
    And set the bot to receive all messages in group: /setprivacy
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[WARNING] Telegram bot not configured. Skipping command handler.")
        return
    
    update_id = None
    print("[*] Telegram command listener started")
    
    try:
        while True:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if update_id:
                params["offset"] = update_id + 1
            
            try:
                response = requests.get(url, params=params, timeout=35)
                if response.status_code == 200:
                    updates = response.json().get("result", [])
                    retry_delay = 5  # Reset delay on successful connection
                    
                    for update in updates:
                        update_id = update.get("update_id")
                        message = update.get("message", {})
                        text = message.get("text", "").strip()
                        chat_id = message.get("chat", {}).get("id")
                        chat_type = message.get("chat", {}).get("type")  # personal, group, supergroup, channel
                        
                        # Only process commands
                        if not text.startswith("/"):
                            continue
                        
                        if not chat_id:
                            print(f"[!] Received command but no chat_id: {text}")
                            continue
                        
                        # Handle group chat format: /command@botname -> /command
                        # Extract just the command part before @
                        command_text = text.split("@")[0] if "@" in text else text
                        
                        print(f"[*] Received '{command_text}' from {chat_type} chat (ID: {chat_id})")
                        
                        if command_text == "/start" and chat_id:
                            reply = (
                                "🤖 Internet Monitor Bot\n\n"
                                "Available commands:\n"
                                "/wifistatus - Show connection and WiFi status\n"
                                "/help - Show this help message"
                            )
                            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            send_data = {
                                "chat_id": chat_id,
                                "text": reply
                            }
                            try:
                                requests.post(send_url, data=send_data, timeout=10)
                                print(f"[✓] Responded to /start command")
                            except Exception as e:
                                print(f"[✗] Error responding to /start: {e}")
                        
                        elif command_text == "/help" and chat_id:
                            reply = (
                                "🤖 Internet Monitor Bot\n\n"
                                "Available commands:\n"
                                "/wifistatus - Show connection and WiFi status\n"
                                "/help - Show this help message"
                            )
                            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            send_data = {
                                "chat_id": chat_id,
                                "text": reply
                            }
                            try:
                                requests.post(send_url, data=send_data, timeout=10)
                                print(f"[✓] Responded to /help command")
                            except Exception as e:
                                print(f"[✗] Error responding to /help: {e}")
                        
                        elif command_text == "/wifistatus" and chat_id:
                            # Send initial "checking" message
                            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            checking_data = {
                                "chat_id": chat_id,
                                "text": "⏳ Checking internet connection..."
                            }
                            try:
                                requests.post(send_url, data=checking_data, timeout=10)
                            except Exception as e:
                                print(f"[✗] Error sending 'checking' message: {e}")
                            
                            # Perform the actual check
                            is_connected = check_internet_connection(consecutive_pings=10)
                            current_ssid = get_current_wifi()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            status_icon = "✅" if is_connected else "❌"
                            reply = (
                                f"{status_icon} Connection Status\n"
                                f"Internet: {'Connected' if is_connected else 'Disconnected'}\n"
                                f"WiFi: {current_ssid if current_ssid else 'Not connected'}\n"
                                f"Time: {timestamp}"
                            )
                            send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            send_data = {
                                "chat_id": chat_id,
                                "text": reply
                            }
                            try:
                                requests.post(send_url, data=send_data, timeout=10)
                                print(f"[✓] Responded to /wifistatus command")
                            except Exception as e:
                                print(f"[✗] Error responding to /wifistatus: {e}")
                else:
                    # Handle Telegram API errors
                    response_data = response.json() if response.text else {}
                    error_code = response_data.get("error_code")
                    error_desc = response_data.get("description", "Unknown error")
                    
                    if error_code == 409:
                        # Conflict: another bot instance is running
                        print(f"[✗] CONFLICT (409): Another bot instance is running!")
                        print(f"    {error_desc}")
                        print("[!] Make sure only ONE instance of netchange is running.")
                        time.sleep(30)  # Wait 30 seconds before retrying
                    else:
                        print(f"[✗] Telegram API error {error_code}: {error_desc}")
                        time.sleep(5)
            
            except requests.exceptions.Timeout:
                pass  # Timeout is expected with long polling
            except requests.exceptions.ConnectionError as e:
                print(f"[⚠] Telegram connection error. Retrying in 5s...")
                time.sleep(5)
            except Exception as e:
                print(f"[✗] Error in telegram command handler: {e}")
                time.sleep(5)
    
    except KeyboardInterrupt:
        print("[*] Telegram command listener stopped")
    except Exception as e:
        print(f"[✗] Telegram command listener error: {e}")

# ===== INTERNET CHECK FUNCTIONS =====
def check_internet_connection(total_pings=TOTAL_PING, max_failed_pings=MAX_FAILED_PINGS):

    # Safety guards
    if total_pings < 1:
        total_pings = 1

    if max_failed_pings < 0:
        max_failed_pings = 0

    if max_failed_pings > total_pings:
        max_failed_pings = total_pings

    failed_pings = 0

    for i in range(total_pings):
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", str(PING_TIMEOUT * 1000), NTP_SERVER],
                    capture_output=True,
                    timeout=PING_TIMEOUT + 2
                )
            else:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", str(PING_TIMEOUT), NTP_SERVER],
                    capture_output=True,
                    timeout=PING_TIMEOUT + 2
                )

            if result.returncode != 0:
                failed_pings += 1

        except Exception:
            failed_pings += 1

        # Early exit if failure threshold reached
        if failed_pings >= max_failed_pings:
            print(f"[✗] Ping failed ({failed_pings}/{total_pings} failures)")
            return False

    # Reached end → internet OK
    if failed_pings > 0:
        print(f"[i] Ping results: {total_pings - failed_pings}/{total_pings} successful")

    return True


# ===== WIFI FUNCTIONS =====
def connect_to_wifi(ssid):
    """
    Connect to a WiFi network.
    - Windows: Uses netsh command
    - Linux: Uses nmcli command (requires sudo)
    """
    try:
        print(f"[*] Attempting to connect to WiFi: {ssid}")
        
        if sys.platform == "win32":
            # Windows WiFi connection using netsh
            cmd = ["netsh", "wlan", "connect", f"name={ssid}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"[✓] Successfully connected to {ssid}")
                return True
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                print(f"[✗] Failed to connect to {ssid}")
                print(f"    Error: {error_msg}")
                return False
        else:
            # Linux - uses nmcli (requires sudo)
            cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"[✓] Successfully connected to {ssid}")
                return True
            else:
                print(f"[✗] Failed to connect to {ssid}")
                print(f"    Error: {result.stderr}")
                return False
    except Exception as e:
        print(f"[✗] Error connecting to WiFi: {e}")
        return False

def get_current_wifi():
    """Get the currently connected WiFi network name on wlan0 only."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if "SSID" in line and ":" in line:
                    return line.split(":", 1)[1].strip()
        else:
            # Get active connection on wlan0 specifically
            result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,NAME", "connection", "show", "--active"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Filter for wlan0 interface only
                for line in result.stdout.strip().split('\n'):
                    if line.startswith("wlan0:"):
                        return line.split(":", 1)[1].strip()
            return None
    except Exception as e:
        print(f"[✗] Error getting current WiFi: {e}")
        return None

def main():
    """Main monitoring loop."""
    print("=" * 60)
    print(f"Internet Connection Monitor (v{VERSION})")
    print(f"Monitoring: {NTP_SERVER}")
    print(f"Primary WiFi: {PRIMARY_WIFI}")
    print(f"Secondary WiFi: {SECONDARY_WIFI}")
    print(f"Fallback WiFi: {FALLBACK_WIFI}")
    print(f"Ping Interval: {PING_INTERVAL} seconds")
    print(f"Retry Primary Every: {RETRY_PRIMARY_INTERVAL // 3600} hours")
    print(f"Ping Strategy: {TOTAL_PING} consecutive pings per check")
    print(f"WiFi Switch Trigger: {MAX_FAILED_PINGS} or more failed pings (out of {TOTAL_PING})")
    print("Token loaded:", bool(os.getenv("TELEGRAM_BOT_TOKEN_NETCHANGE")))         # checks if telegram bot token is loaded correctly from /etc/netchange.env
    print("=" * 60)
    print()
    
    connection_was_good = True
    last_ssid = None
    last_primary_retry = 0
    
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_time = time.time()
            
            # Check internet connection with 10 consecutive pings
            is_connected = check_internet_connection(consecutive_pings=10)
            current_ssid = get_current_wifi()
            
            # Check if it's time to retry primary WiFi
            should_retry_primary = (current_time - last_primary_retry) >= RETRY_PRIMARY_INTERVAL
            
            if is_connected:
                if not connection_was_good:
                    print(f"[{timestamp}] ✓ Internet connection RESTORED")
                    message = f"✅ Internet connection restored!\nWiFi: {current_ssid}\nTime: {timestamp}"
                    send_telegram_message(message, skip_queue=True)
                    # Flush any pending messages that were queued while offline
                    flush_pending_messages()
                    connection_was_good = True
                else:
                    print(f"[{timestamp}] ✓ Connected (WiFi: {current_ssid})")
                
                # If on fallback WiFi and it's time to retry primary, attempt to switch
                if current_ssid == FALLBACK_WIFI and should_retry_primary:
                    print(f"[{timestamp}] → Attempting to reconnect to {PRIMARY_WIFI}")
                    message = f"🔄 Attempting to switch to {PRIMARY_WIFI}...\nTime: {timestamp}"
                    send_telegram_message(message)
                    
                    if connect_to_wifi(PRIMARY_WIFI):
                        time.sleep(5)  # Wait for connection to establish
                        current_ssid = get_current_wifi()
                        
                        if current_ssid == PRIMARY_WIFI:
                            # Check if primary WiFi has internet
                            time.sleep(2)
                            if check_internet_connection(consecutive_pings=10):
                                print(f"[{timestamp}] ✓ Switched to {PRIMARY_WIFI} with internet!")
                                message = f"✅ Successfully switched to {PRIMARY_WIFI}!\nTime: {timestamp}"
                                send_telegram_message(message)
                                last_primary_retry = current_time
                                consecutive_failures = 0
                            else:
                                print(f"[{timestamp}] ✗ {PRIMARY_WIFI} has no internet, staying on {FALLBACK_WIFI}")
                                message = f"⚠️ {PRIMARY_WIFI} has no internet. Staying on {FALLBACK_WIFI}\nTime: {timestamp}"
                                send_telegram_message(message)
                                connect_to_wifi(FALLBACK_WIFI)
                        else:
                            print(f"[{timestamp}] ✗ Failed to switch to {PRIMARY_WIFI}")
                    else:
                        print(f"[{timestamp}] ✗ Could not connect to {PRIMARY_WIFI}")
                    
                    last_primary_retry = current_time
            
            else:
                # Ping check failed (5+ pings failed out of 10)
                print(f"[{timestamp}] ✗ Ping check failed - attempting WiFi switch")
                
                if connection_was_good:
                    print(f"[{timestamp}] ✗ Internet connection LOST")
                    message = f"⚠️ Internet connection lost!\nTime: {timestamp}"
                    send_telegram_message(message)
                    connection_was_good = False
                
                # Try to connect in priority order: PRIMARY -> SECONDARY -> FALLBACK
                wifi_priority = [
                    (PRIMARY_WIFI, "Priority 1"),
                    (SECONDARY_WIFI, "Priority 2"),
                    (FALLBACK_WIFI, "Priority 3")
                ]
                
                connected = False
                for wifi_ssid, priority_name in wifi_priority:
                    if connected:
                        break
                    
                    if not current_ssid or current_ssid != wifi_ssid:
                        print(f"[{timestamp}] → Attempting to connect to {wifi_ssid} ({priority_name})")
                        if connect_to_wifi(wifi_ssid):
                            time.sleep(5)  # Wait for connection
                            current_ssid = get_current_wifi()
                            
                            if current_ssid == wifi_ssid:
                                time.sleep(2)
                                if check_internet_connection(consecutive_pings=10):
                                    print(f"[{timestamp}] ✓ Connected to {wifi_ssid}")
                                    message = f"✅ Connected to {wifi_ssid}!\nTime: {timestamp}"
                                    send_telegram_message(message, skip_queue=True)
                                    # Flush pending messages after successful reconnection
                                    flush_pending_messages()
                                    if wifi_ssid == PRIMARY_WIFI:
                                        last_primary_retry = current_time
                                    connected = True
                                else:
                                    print(f"[{timestamp}] ✗ {wifi_ssid} has no internet, trying next priority")
                
                # Check if we switched WiFi networks
                if current_ssid and last_ssid != current_ssid:
                    if current_ssid == PRIMARY_WIFI:
                        print(f"[{timestamp}] → Switched to {PRIMARY_WIFI}")
                    elif current_ssid == SECONDARY_WIFI:
                        print(f"[{timestamp}] → Switched to {SECONDARY_WIFI}")
                    elif current_ssid == FALLBACK_WIFI:
                        print(f"[{timestamp}] → Switched to {FALLBACK_WIFI}")
                    last_ssid = current_ssid
            
            # Update last_ssid for next iteration
            if current_ssid:
                last_ssid = current_ssid
            
            # Wait before next check
            time.sleep(PING_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n[*] Monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[✗] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Start Telegram command handler in a separate thread
    telegram_thread = threading.Thread(target=handle_telegram_commands, daemon=True)
    telegram_thread.start()
    
    # Start main monitoring loop in main thread
    main()
