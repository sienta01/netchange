# 📜 CHANGELOG

All notable changes to this project will be documented in this file.

---

## [1.3.0] – 2025-12-30

### 🛠 Fixed
- Fixed SSID re-scan. Now waits 10 seconds for network to appear
- Fixed bug for consecutive_ping

---

## [1.2.1] – 2025-12-30

### 🔄 Changed
- Banner rearranged to look neater

### 🛠 Fixed
- Fixed SSID re-scan previledge (sudo)

---

## [1.2.0] – 2025-12-29

### 🛠 Fixed
- Added Wi-Fi rescan before switching to prevent no SSID found

---

## [1.1.1] – 2025-12-29

### ✨ Added
- Version number in start banner

### 🔄 Changed
- Telegram bot token now using os environment

---

## [1.1.0] – 2025-12-29

### ✨ Added
- Configurable total ping count (`TOTAL_PING`)
- Configurable failure threshold (`MAX_FAILED_PINGS`)
- Improved internet check logic with early-exit optimization

### 🔄 Changed
- Refactored `check_internet_connection()` to accept:
  - `total_pings`
  - `max_failed_pings`
- WiFi failover decision now based on configurable thresholds
- Ping timeout increased for unstable networks

### 🛠 Fixed
- Logical inconsistency between ping count and failure threshold
- Edge cases where invalid ping values caused false positives
- Function parameter mismatch (`consecutive_pings` → `total_pings`)
- Removed unused variables causing confusion
- Corrected misleading comments and log messages
- Improved error handling during ping execution

---

## [1.0.0] – 2025-12-29

### 🎉 Initial Release
- Internet connectivity monitoring using ICMP ping
- Automatic WiFi switching with priority order:
  - Primary
  - Secondary
  - Fallback
- Telegram notifications for:
  - Connection loss
  - Connection restore
  - WiFi changes
- Telegram bot commands:
  - `/start`
  - `/help`
  - `/wifistatus`
- Offline message queue with delayed delivery
- Cross-platform ping support (Linux / Windows)
- Background Telegram command listener thread