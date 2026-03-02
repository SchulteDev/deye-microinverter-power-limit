# Deye Microinverter — Modbus Register Reference

## Register 40 (0x0028) — Active Power Regulation — CONFIRMED

**Independently confirmed by multiple sources:**

1. **kbialek/deye-inverter-mqtt** — `metric_group_settings_micro.md`: Register 40 = "Active power regulation", unit %, scale 1
2. **davidrapan/ha-solarman** — `deye_micro.yaml`: Register 0x0028 = "Active Power Regulation", range 0–120%
3. **StephanJoubert/home_assistant_solarman** — `deye_2mppt.yaml` and `deye_4mppt.yaml`: Register 0x0028
4. **raschy/ioBroker.deyeidc** — Issue #88: Users confirm writing to register 40
5. **Akkudoktor Forum** — "You can control the power via register 40 Active Power Regulation"
6. **Deye Modbus Protocol V118 PDF** (official document, hosted at Hypfer/deye-microinverter-cloud-free-assets)

---

## All Modbus Registers

All registers are read via Modbus Function Code 0x03. Writing uses FC 0x10 (Write Multiple Registers). Communication is over the Solarman V5 protocol (TCP port 8899).

### Device Information (read-only)

| Reg | Hex | Name | Unit | Scale | Type |
|-----|-----|------|------|-------|------|
| 0 | 0x0000 | Device Type | — | 1 | U16 |
| 1 | 0x0001 | Modbus Address | — | 1 | U16 |
| 2 | 0x0002 | Protocol Version | — | 1 | Version |
| 3–7 | 0x0003–0x0007 | Inverter Serial Number | — | 1 | ASCII (5 reg) |
| 8 | 0x0008 | Device Flags | — | 1 | U16 |
| 9 | 0x0009 | Chip Type | — | 1 | U16 |
| 10–14 | 0x000A–0x000E | Firmware Versions | — | 1 | Version |
| 16–17 | 0x0010–0x0011 | Rated Power | W | 0.1 | U32 |
| 18 | 0x0012 | MPPT Count / Phases | — | 1 | U16 |

### Configuration (read/write)

| Reg | Hex | Name | Unit | Scale | Range | Notes |
|-----|-----|------|------|-------|-------|-------|
| 21 | 0x0015 | Self-Test Time (Startup) | s | 1 | 0–1000 | |
| 22–24 | 0x0016–0x0018 | Date & Time | — | 1 | Special | YM/DH/MS encoded |
| 27 | 0x001B | Grid Voltage Upper Limit | V | 0.1 | 160–550 | |
| 28 | 0x001C | Grid Voltage Lower Limit | V | 0.1 | 160–550 | |
| 29 | 0x001D | Grid Frequency Upper Limit | Hz | 0.01 | 45–65 | |
| 30 | 0x001E | Grid Frequency Lower Limit | Hz | 0.01 | 45–65 | |
| 34 | 0x0022 | Over-Frequency Load Reduction Start | Hz | 0.01 | 45–65 | |
| 35 | 0x0023 | Over-Frequency Load Reduction % | % | 1 | 0–100 | |
| 39 | 0x0027 | Power Factor (cos φ) | — | 0.001 | −1.0 to +1.0 | Offset 1000 |
| **40** | **0x0028** | **Active Power Regulation** | **%** | **1** | **1–100** | **Power output limit (values >100 are rejected / clamped to 100)** |
| 43 | 0x002B | On/Off Switch | — | 1 | 1=On, 2=Off | Turn inverter on/off |
| 46 | 0x002E | Anti-Islanding | — | 1 | 0=Off, 1=On | |
| 47 | 0x002F | Soft Start | — | 1 | 0=Off, 1=On | |
| 48 | 0x0030 | GFDI (Ground Fault Detection) | — | 1 | 0=Off, 1=On | |
| 49 | 0x0031 | Over-Frequency Load Shedding | — | 1 | 0=Off, 1=On | |
| 50 | 0x0032 | RISO (Insulation Monitoring) | — | 1 | 0=Off, 1=On | |
| 54 | 0x0036 | EEPROM / Factory Reset | — | 1 | 0/1/2 | 1=Control board, 2=Comm board reset |

### Status / Monitoring (read-only)

| Reg | Hex | Name | Unit | Scale | Type |
|-----|-----|------|------|-------|------|
| 59 | 0x003B | Operating Status | — | 1 | U16 |
| 60 | 0x003C | Daily Yield (total) | kWh | 0.1 | U16 |
| 62 | 0x003E | Operating Time | min | 1 | U16 |
| 63–64 | 0x003F–0x0040 | Total Yield | kWh | 0.1 | U32 |
| 65–68 | 0x0041–0x0044 | Daily Yield PV1–PV4 | kWh | 0.1 | U16 |
| 69–78 | 0x0045–0x004E | Total Yield PV1–PV4 | kWh | 0.1 | U32 |
| 73 | 0x0049 | AC Grid Voltage | V | 0.1 | U16 |
| 76 | 0x004C | AC Grid Current | A | 0.1 | S16 |
| 79 | 0x004F | Grid Frequency | Hz | 0.01 | U16 |
| 80 | 0x0050 | Operating Power | W | 0.1 | U16 |
| 86–87 | 0x0056–0x0057 | AC Active Power (total) | W | 0.1 | U32 |
| 90 | 0x005A | Heatsink Temperature | °C | 0.01 | U16 |
| 101–102 | 0x0065–0x0066 | Alarm Code | — | 1 | U32 |
| 103–106 | 0x0067–0x006A | Fault Code | — | 1 | U64 |
| 109 | 0x006D | PV1 Voltage | V | 0.1 | U16 |
| 110 | 0x006E | PV1 Current | A | 0.1 | U16 |
| 111 | 0x006F | PV2 Voltage | V | 0.1 | U16 |
| 112 | 0x0070 | PV2 Current | A | 0.1 | U16 |
| 113 | 0x0071 | PV3 Voltage | V | 0.1 | U16 |
| 114 | 0x0072 | PV3 Current | A | 0.1 | U16 |
| 115 | 0x0073 | PV4 Voltage | V | 0.1 | U16 |
| 116 | 0x0074 | PV4 Current | A | 0.1 | U16 |

### Operating Status Values (Register 59)

| Value | Meaning |
|-------|---------|
| 0 | Standby |
| 1 | Self-Test |
| 2 | Normal |
| 3 | Warning / Alarm |
| 4 | Fault |

---

## Full Configuration Without a Business Account

**No authentication is required over Modbus TCP (port 8899).** The only "key" is the logger serial number used in the Solarman V5 protocol.

Everything hidden behind the "Installer" / "Business" login in the Solarman app can be written directly via Modbus:

| Setting | App: Business account required? | Modbus: freely accessible? |
|---------|--------------------------------|----------------------------|
| Power limit | Yes | **Yes** (Reg 40) |
| On/Off switch | Yes | **Yes** (Reg 43) |
| Power factor (cos φ) | Yes | **Yes** (Reg 39) |
| Grid voltage limits | Yes | **Yes** (Reg 27–28) |
| Grid frequency limits | Yes | **Yes** (Reg 29–30) |
| Anti-islanding | Yes | **Yes** (Reg 46) |
| Over-frequency load shedding | Yes | **Yes** (Reg 34–35, 49) |
| Soft start | Yes | **Yes** (Reg 47) |
| GFDI ground fault detection | Yes | **Yes** (Reg 48) |
| Insulation monitoring | Yes | **Yes** (Reg 50) |
| Factory reset | Yes | **Yes** (Reg 54) |
| Date / time | No | **Yes** (Reg 22–24) |

---

## Sources

### Primary Sources (code/YAML with register definitions)
- [kbialek/deye-inverter-mqtt](https://github.com/kbialek/deye-inverter-mqtt) — metric_group_settings_micro.md
- [davidrapan/ha-solarman — deye_micro.yaml](https://github.com/davidrapan/ha-solarman) — references Deye Modbus Protocol V118
- [StephanJoubert/home_assistant_solarman](https://github.com/StephanJoubert/home_assistant_solarman) — deye_2mppt.yaml, deye_4mppt.yaml
- [Deye Modbus Protocol V118 PDF](https://github.com/Hypfer/deye-microinverter-cloud-free-assets) — official protocol document

### Additional Sources
- [Hypfer/deye-microinverter-cloud-free](https://github.com/Hypfer/deye-microinverter-cloud-free) — cloud-free operation
- [pysolarmanv5 Documentation](https://pysolarmanv5.readthedocs.io/)
- [DIY Solar Forum — Controlling Deye micro-inverter via Modbus](https://diysolarforum.com/threads/controlling-deye-micro-inverter-via-modbus-using-python-script.106237/)
