# Modbus Register Reference

## Register 40 (0x0028) — Active Power Regulation

| Field   | Value                   |
|---------|-------------------------|
| Address | 40 (0x0028)             |
| Name    | Active Power Regulation |
| Unit    | %                       |
| Scale   | 1                       |
| Range   | 1–100                   |
| Access  | Read/Write              |

The register value directly sets the inverter's maximum AC output as a percentage of its rated
power. Values above 100 are rejected or clamped to 100. The value is persisted to EEPROM (see
the [EEPROM warning](README.md#eeprom-wear-warning) in the README).

Read with Modbus function code 0x03, write with FC 0x10. Communication uses the Solarman V5 protocol
over TCP port 8899.

## Register 16 (0x0010) — Device Rated Power

| Field   | Value                             |
|---------|-----------------------------------|
| Address | 16 (0x0010)                       |
| Name    | Device Rated Power                |
| Unit    | W                                 |
| Scale   | 0.1                               |
| Range   | 1–2250 W (per ha-solarman source) |
| Access  | Read                              |

The inverter's nameplate power rating. A 1000 W inverter returns raw value `10000` → 1000 W.
Read with FC 0x03. This is used as a best-effort lookup when `--max-power` is not provided — the
read may not be supported on all logger firmware versions. The tool accepts values in the range
10–10000 W.

Source: [davidrapan/ha-solarman](https://github.com/davidrapan/ha-solarman) — deye_micro.yaml.

## Sources

- [Deye Modbus Protocol V118 PDF](https://github.com/Hypfer/deye-microinverter-cloud-free-assets)
  — official protocol document
- [kbialek/deye-inverter-mqtt](https://github.com/kbialek/deye-inverter-mqtt)
  — metric_group_settings_micro.md
- [davidrapan/ha-solarman](https://github.com/davidrapan/ha-solarman) — deye_micro.yaml
- [pysolarmanv5](https://pysolarmanv5.readthedocs.io/) — Solarman V5 protocol reference
