"""Unit tests for Modbus and Solarman V5 protocol functions."""

import struct
import sys
from pathlib import Path

import pytest

# Make the single-file script importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deye_power_limit import (
    build_modbus_read,
    build_modbus_write_multiple,
    build_modbus_write_single,
    modbus_crc16,
    parse_modbus_read_response,
    v5_build_frame,
    v5_decode_response,
)


# ========== Modbus CRC ==========

def test_modbus_crc16_known_value():
    """Verify CRC against a known Modbus read request (slave=1, FC03, reg=40, count=1)."""
    frame = bytes([0x01, 0x03, 0x00, 0x28, 0x00, 0x01])
    assert modbus_crc16(frame) == bytes.fromhex("0402")


def test_modbus_crc16_empty():
    """CRC of empty data should be 0xFFFF (initial value, no XOR)."""
    assert modbus_crc16(b"") == struct.pack("<H", 0xFFFF)


def test_modbus_crc16_single_byte():
    """CRC should be deterministic for a single byte."""
    crc = modbus_crc16(b"\x01")
    assert len(crc) == 2
    # Verify round-trip: CRC of (data + crc) should produce a fixed residue
    assert modbus_crc16(b"\x01" + crc) == b"\x00\x00"


# ========== Modbus Frame Builders ==========

def test_build_modbus_read():
    """Read Holding Registers: slave=1, register=40, count=1."""
    frame = build_modbus_read(1, 40, 1)
    assert frame == bytes.fromhex("0103002800010402")
    assert frame[0] == 0x01  # slave
    assert frame[1] == 0x03  # function code


def test_build_modbus_write_single():
    """Write Single Register: slave=1, register=40, value=50."""
    frame = build_modbus_write_single(1, 40, 50)
    assert frame == bytes.fromhex("0106002800328817")
    assert frame[0] == 0x01  # slave
    assert frame[1] == 0x06  # function code


def test_build_modbus_write_multiple():
    """Write Multiple Registers: slave=1, register=40, values=[50]."""
    frame = build_modbus_write_multiple(1, 40, [50])
    assert frame == bytes.fromhex("01100028000102003221ad")
    assert frame[0] == 0x01   # slave
    assert frame[1] == 0x10   # function code
    assert frame[4:6] == b"\x00\x01"  # register count = 1
    assert frame[6] == 0x02   # byte count = 2


def test_build_modbus_write_multiple_two_values():
    """Write Multiple Registers with two values to verify byte count."""
    frame = build_modbus_write_multiple(1, 40, [50, 100])
    assert frame[1] == 0x10
    assert frame[4:6] == b"\x00\x02"  # register count = 2
    assert frame[6] == 0x04           # byte count = 4


# ========== V5 Frame ==========

def test_v5_build_frame_structure():
    """Verify V5 frame start byte, end byte, and serial encoding."""
    modbus = build_modbus_read(1, 40, 1)
    frame = v5_build_frame(123456789, modbus)

    assert frame[0] == 0xA5    # start byte
    assert frame[-1] == 0x15   # end byte

    # Serial is at bytes 7..11, little-endian
    serial = struct.unpack("<I", frame[7:11])[0]
    assert serial == 123456789


def test_v5_build_frame_length():
    """Length field should equal 15 + len(modbus_frame)."""
    modbus = build_modbus_read(1, 40, 1)
    frame = v5_build_frame(123456789, modbus)

    length = struct.unpack("<H", frame[1:3])[0]
    assert length == 15 + len(modbus)


def test_v5_build_frame_checksum():
    """Checksum is sum of bytes[1..len-3] & 0xFF."""
    modbus = build_modbus_read(1, 40, 1)
    frame = v5_build_frame(123456789, modbus)

    expected_checksum = sum(frame[1:-2]) & 0xFF
    assert frame[-2] == expected_checksum


def test_v5_build_frame_control_code():
    """Control code should be 0x4510 (request)."""
    modbus = build_modbus_read(1, 40, 1)
    frame = v5_build_frame(123456789, modbus)

    control = struct.unpack("<H", frame[3:5])[0]
    assert control == 0x4510


# ========== V5 Response Decoding ==========

def _build_v5_response(serial: int, modbus_frame: bytes) -> bytes:
    """Build a synthetic V5 response frame for testing."""
    # Response has 14-byte payload header + modbus
    payload_hdr = bytes([0x02]) + b"\x00" * 13
    payload = payload_hdr + modbus_frame
    payload_len = len(payload)

    resp = bytearray()
    resp.append(0xA5)
    resp.extend(struct.pack("<H", payload_len))
    resp.extend(struct.pack("<H", 0x1510))       # response control code
    resp.extend(struct.pack("<H", 0x01))          # sequence
    resp.extend(struct.pack("<I", serial))
    resp.extend(payload)
    resp.append(0x00)   # checksum placeholder
    resp.append(0x15)   # end byte

    checksum = sum(resp[1:-2]) & 0xFF
    resp[-2] = checksum
    return bytes(resp)


def test_v5_decode_response_roundtrip():
    """Build a V5 response, decode it, verify we get the modbus frame back."""
    modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32]) + modbus_crc16(
        bytes([0x01, 0x03, 0x02, 0x00, 0x32])
    )
    response = _build_v5_response(123456789, modbus)
    decoded = v5_decode_response(response)
    assert decoded == modbus


def test_v5_decode_response_invalid_start():
    """Non-0xA5 start byte should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid V5 frame"):
        v5_decode_response(bytes([0x00] * 30))


def test_v5_decode_response_invalid_end():
    """Wrong end byte should raise ValueError."""
    modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
    response = bytearray(_build_v5_response(123456789, modbus))
    response[-1] = 0x00  # break end byte
    with pytest.raises(ValueError, match="invalid end byte"):
        v5_decode_response(bytes(response))


def test_v5_decode_response_wrong_control_code():
    """Non-response control code should raise ValueError."""
    modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
    response = bytearray(_build_v5_response(123456789, modbus))
    # Overwrite control code with request code 0x4510
    response[3:5] = struct.pack("<H", 0x4510)
    with pytest.raises(ValueError, match="V5 control code"):
        v5_decode_response(bytes(response))


# ========== Modbus Response Parsing ==========

def test_parse_modbus_read_response_single():
    """Parse response with a single register value of 50."""
    # slave=1, func=3, bytecount=2, value=50 (0x0032), + CRC
    frame = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
    values = parse_modbus_read_response(frame)
    assert values == [50]


def test_parse_modbus_read_response_multiple():
    """Parse response with two register values."""
    # slave=1, func=3, bytecount=4, val1=100 (0x0064), val2=200 (0x00C8), + CRC
    body = bytes([0x01, 0x03, 0x04, 0x00, 0x64, 0x00, 0xC8])
    crc = modbus_crc16(body)
    frame = body + crc
    values = parse_modbus_read_response(frame)
    assert values == [100, 200]


def test_parse_modbus_error_response():
    """Error response (function code with high bit set) should raise ValueError."""
    # slave=1, func=0x83 (error for FC03), error_code=2 (Illegal Data Address)
    frame = bytes([0x01, 0x83, 0x02])
    with pytest.raises(ValueError, match="Illegal Data Address"):
        parse_modbus_read_response(frame)


def test_parse_modbus_error_unknown_code():
    """Unknown error codes should still raise with a code number."""
    frame = bytes([0x01, 0x83, 0x09])
    with pytest.raises(ValueError, match="Code 9"):
        parse_modbus_read_response(frame)
