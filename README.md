[![CI](https://github.com/SchulteDev/deye-microinverter-power-limit/actions/workflows/ci.yml/badge.svg)](https://github.com/SchulteDev/deye-microinverter-power-limit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue.svg)](https://ghcr.io)

# Deye Microinverter Power Limit

Set the power output limit on Deye microinverters via Solarman V5 / Modbus.

## What This Does

A single-file, zero-dependency Python CLI that writes to **Modbus register 40** (Active Power
Regulation) on Deye microinverters through the Solarman V5 protocol. This lets you limit the
inverter's AC output to any percentage (1–100%) without needing the Solarman app or a business
account.

Works with any Deye microinverter that has a Solarman-compatible data logger (e.g. SUN300G3,
SUN600G3, SUN1600G3, SUN2000G3).

## Prerequisites

- **Python 3.12+** (no third-party packages required)
- The Solarman data logger must be reachable on your **local network** (TCP port 8899)
- You need the logger's **IP address** and **serial number**

## Usage

```bash
# Read current power limit
python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --read-only

# Set power limit to 50%
python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --percent 50

# Set to 50% and show watts (optional convenience for a 1600 W inverter)
python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --percent 50 --max-power 1600

# Remove limit (full power)
python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --percent 100
```

### `.env` File (optional)

Copy `.env.example` to `.env` and fill in your values to avoid repeating `--ip` and `--serial`:

```bash
cp .env.example .env   # then edit .env
python deye_power_limit.py --read-only
python deye_power_limit.py --percent 50
```

CLI arguments always override `.env` / environment variables.

### Example run

```
$ python deye_power_limit.py --percent 80 --max-power 1000

Reading register 40 from 192.168.1.x (logger 4567890123) ...
  AT greeting received, discarded.
Current register value: 80
  = 80% = max 800 W

Setting power limit to 80% (max 800 W) ...
  Writing register 40 = 80
  AT greeting received, discarded.
  Register 40 = 80 write command sent.
  Verifying ...
  AT greeting received, discarded.
  Read-back value: 80%

Success! Power limited to max 800 W.
```

## Docker

```bash
# Build
docker build -t deye-microinverter-power-limit .

# Run
docker run --rm --network host deye-microinverter-power-limit \
  --ip 192.168.1.X --serial 1234567890 --percent 50
```

Or pull from GHCR:

```bash
docker run --rm --network host ghcr.io/schultedev/deye-microinverter-power-limit:main \
  --ip 192.168.1.X --serial 1234567890 --read-only
```

## Finding Your Logger Serial & IP

| Method             | Steps                                                                      |
|--------------------|----------------------------------------------------------------------------|
| **Solarman app**   | Device list → tap your logger → "Device information" → Serial number       |
| **Logger sticker** | The 10-digit number printed on the logger stick                            |
| **Router DHCP**    | Look for a device with hostname starting with `S` or MAC prefix `E8:FD:F8` |

The serial number is a **10-digit integer** (e.g. `4140346640`), not the inverter's serial.

## Modbus Register Reference

See [MODBUS_REGISTERS.md](MODBUS_REGISTERS.md) for register details and sources.

## EEPROM Wear Warning

Register 40 writes are **persisted to EEPROM**. EEPROM has limited write cycles (typically
100,000–1,000,000). If you use this for zero-export control, **do not write every second**.
Recommendations:

- Only write when the value actually changes
- Use coarser steps (e.g. 5% instead of 1%)
- Wait at least 30 seconds between writes

## Development

```bash
# Install dev dependencies
pip install pytest

# Run tests
pytest
```
