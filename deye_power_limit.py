#!/usr/bin/env python3
"""
Deye Microinverter — Set power output limit via Solarman V5 / Modbus
=====================================================================
Standalone implementation based on the pysolarmanv5 source code.
Communicates over TCP port 8899 with the Solarman data logger.

Usage:
    python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --read-only
    python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --percent 50
    python deye_power_limit.py --ip 192.168.1.X --serial 1234567890 --percent 50 --max-power 1600
"""

import argparse
import socket
import struct
import sys
import time

# ---------- Constants ----------
REGISTER_ADDR = 40          # Holding register "Active Power Regulation"
PORT = 8899                 # Solarman V5 default port
MB_SLAVE_ID = 1             # Modbus slave ID


# ========== Modbus RTU ==========

def modbus_crc16(data: bytes) -> bytes:
    """Calculate Modbus CRC-16 (polynomial 0xA001)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return struct.pack("<H", crc)


def build_modbus_read(slave: int, register: int, count: int) -> bytes:
    """Function 0x03: Read Holding Registers."""
    frame = struct.pack(">B B H H", slave, 0x03, register, count)
    return frame + modbus_crc16(frame)


def build_modbus_write_multiple(slave: int, register: int, values: list[int]) -> bytes:
    """Function 0x10: Write Multiple Registers."""
    count = len(values)
    byte_count = count * 2
    frame = struct.pack(">B B H H B", slave, 0x10, register, count, byte_count)
    for v in values:
        frame += struct.pack(">H", v)
    return frame + modbus_crc16(frame)


# ========== Solarman V5 Protocol ==========

def v5_build_frame(serial: int, modbus_frame: bytes, seq: int = 0x01) -> bytes:
    """Build a Solarman V5 frame — matches pysolarmanv5._v5_frame_encoder."""
    # Payload (15 bytes header + modbus)
    payload = bytearray()
    payload.append(0x02)                        # frametype
    payload.extend(b'\x00\x00')                 # sensortype
    payload.extend(b'\x00\x00\x00\x00')         # deliverytime
    payload.extend(b'\x00\x00\x00\x00')         # powerontime
    payload.extend(b'\x00\x00\x00\x00')         # offsettime
    payload.extend(modbus_frame)

    # Header
    frame = bytearray()
    frame.append(0xA5)                                          # v5_start
    frame.extend(struct.pack("<H", 15 + len(modbus_frame)))     # v5_length
    frame.extend(struct.pack("<H", 0x4510))                     # v5_controlcode
    frame.extend(struct.pack("<H", seq))                        # v5_serial (sequence)
    frame.extend(struct.pack("<I", serial))                     # v5_loggerserial

    # Payload
    frame.extend(payload)

    # Trailer (placeholder checksum + end)
    frame.append(0x00)                          # checksum placeholder
    frame.append(0x15)                          # v5_end

    # Checksum: sum of bytes[1] through bytes[len-3]
    checksum = 0
    for i in range(1, len(frame) - 2):
        checksum += frame[i] & 0xFF
    frame[-2] = checksum & 0xFF

    return bytes(frame)


def v5_decode_response(data: bytes) -> bytes:
    """Extract the Modbus frame from a V5 response (offset 25 to len-2)."""
    if len(data) < 10 or data[0] != 0xA5:
        raise ValueError(f"Invalid V5 frame (len={len(data)}, start=0x{data[0]:02X})")

    if data[-1] != 0x15:
        raise ValueError(f"V5 frame: invalid end byte 0x{data[-1]:02X}")

    # Check control code (response = 0x1510)
    control = struct.unpack("<H", data[3:5])[0]
    if control != 0x1510:
        raise ValueError(f"V5 control code 0x{control:04X} (expected 0x1510)")

    # Check frametype (must be 0x02 for data frame)
    if len(data) > 11 and data[11] != 0x02:
        raise ValueError(f"V5 frametype 0x{data[11]:02X} (expected 0x02, not a data frame)")

    # Extract Modbus frame (pysolarmanv5: offset 25 to frame_len-2)
    payload_len = struct.unpack("<H", data[1:3])[0]
    frame_len = 13 + payload_len
    modbus = data[25:frame_len - 2]

    if len(modbus) < 5:
        raise ValueError(f"Modbus frame too short ({len(modbus)} bytes)")

    return modbus


def parse_modbus_read_response(frame: bytes) -> list[int]:
    """Parse a Modbus read response and return register values."""
    function = frame[1]
    if function & 0x80:
        error_code = frame[2]
        errors = {1: "Illegal Function", 2: "Illegal Data Address",
                  3: "Illegal Data Value", 4: "Slave Device Failure"}
        raise ValueError(f"Modbus error: {errors.get(error_code, f'Code {error_code}')}")

    byte_count = frame[2]
    values = []
    for i in range(0, byte_count, 2):
        values.append(struct.unpack(">H", frame[3 + i:5 + i])[0])
    return values


# ========== Communication ==========

def send_receive(ip: str, serial: int, modbus_frame: bytes) -> bytes:
    """Send a V5 frame and wait for a valid Modbus response."""
    seq = 0x01
    v5_frame = v5_build_frame(serial, modbus_frame, seq)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(15)
    try:
        sock.connect((ip, PORT))

        # Discard AT greeting (logger sends it on connect)
        try:
            sock.settimeout(3)
            greeting = sock.recv(1024)
            if greeting and greeting[0] != 0xA5:
                print("  AT greeting received, discarded.")
        except socket.timeout:
            pass

        # Send V5 request
        sock.settimeout(15)
        sock.sendall(v5_frame)

        # Wait for a valid V5 data response (up to 10 frames / 15 seconds)
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                sock.settimeout(max(1, deadline - time.time()))
                data = sock.recv(1024)
            except socket.timeout:
                break

            if not data:
                continue

            # Only accept V5 frames (0xA5) with frametype 0x02
            if data[0] == 0xA5 and len(data) > 11 and data[11] == 0x02:
                return data

        raise ValueError("Timeout: no Modbus response received from logger.")
    finally:
        sock.close()


def read_register(ip: str, serial: int, register: int) -> int:
    mb_request = build_modbus_read(MB_SLAVE_ID, register, 1)
    response = send_receive(ip, serial, mb_request)
    mb_response = v5_decode_response(response)
    values = parse_modbus_read_response(mb_response)
    return values[0]


def write_register(ip: str, serial: int, register: int, value: int) -> None:
    mb_request = build_modbus_write_multiple(MB_SLAVE_ID, register, [value])
    response = send_receive(ip, serial, mb_request)
    try:
        v5_decode_response(response)
    except ValueError:
        # Write response may have a shorter Modbus frame; success is
        # verified by the subsequent read-back.
        pass
    print(f"  Register {register} = {value} written.")


# ========== Main ==========

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set power output limit on Deye microinverters via Solarman V5 / Modbus"
    )
    parser.add_argument("--ip", required=True,
                        help="IP address of the Solarman data logger")
    parser.add_argument("--serial", required=True, type=int,
                        help="Serial number of the data logger")
    parser.add_argument("--percent", type=int, default=None,
                        help="Power limit in percent (1-100)")
    parser.add_argument("--max-power", type=int, default=None,
                        help="Rated inverter power in watts (display only, e.g. 1600)")
    parser.add_argument("--read-only", action="store_true",
                        help="Only read the current register value")
    args = parser.parse_args()

    # --- Read ---
    print(f"Reading register {REGISTER_ADDR} from {args.ip} (logger {args.serial}) ...")
    current = read_register(args.ip, args.serial, REGISTER_ADDR)
    print(f"Current register value: {current}")
    if args.max_power:
        print(f"  = {current}% = max {args.max_power * current / 100:.0f} W")
    else:
        print(f"  = {current}%")
    print()

    if args.read_only:
        print("Read-only mode — no changes made.")
        return

    # --- Write ---
    if args.percent is None:
        parser.error("--percent is required when not using --read-only")

    percent = args.percent

    if not 1 <= percent <= 100:
        print(f"ERROR: percent must be between 1 and 100 (got {percent}).")
        sys.exit(1)

    if args.max_power:
        target_w = args.max_power * percent / 100
        print(f"Setting power limit to {percent}% (max {target_w:.0f} W) ...")
    else:
        print(f"Setting power limit to {percent}% ...")
    print(f"  Writing register {REGISTER_ADDR} = {percent}")
    write_register(args.ip, args.serial, REGISTER_ADDR, percent)

    # --- Verify ---
    print("  Verifying ...")
    time.sleep(1)
    verify = read_register(args.ip, args.serial, REGISTER_ADDR)
    print(f"  Read-back value: {verify}%")

    if verify == percent:
        if args.max_power:
            print(f"\nSuccess! Power limited to max {target_w:.0f} W.")
        else:
            print(f"\nSuccess! Power limited to {percent}%.")
    else:
        print(f"\nWARNING: Read-back value ({verify}) differs from written value ({percent})!")


if __name__ == "__main__":
    main()
