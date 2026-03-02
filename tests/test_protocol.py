"""Unit tests for Modbus and Solarman V5 protocol functions."""

import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deye_power_limit import (
  build_modbus_read,
  build_modbus_write_multiple,
  modbus_crc16,
  parse_modbus_read_response,
  v5_build_frame,
  v5_decode_response,
)


# ========== Modbus CRC ==========

def test_modbus_crc16():
  """Verify CRC against a known Modbus read request (slave=1, FC03, reg=40, count=1)."""
  frame = bytes([0x01, 0x03, 0x00, 0x28, 0x00, 0x01])
  assert modbus_crc16(frame) == bytes.fromhex("0402")


# ========== Modbus Frame Builders ==========

def test_build_modbus_read():
  """Read Holding Registers: slave=1, register=40, count=1."""
  frame = build_modbus_read(1, 40, 1)
  assert frame == bytes.fromhex("0103002800010402")
  assert frame[1] == 0x03  # function code


def test_build_modbus_write_multiple():
  """Write Multiple Registers: slave=1, register=40, values=[50]."""
  frame = build_modbus_write_multiple(1, 40, [50])
  assert frame == bytes.fromhex("01100028000102003221ad")
  assert frame[1] == 0x10  # function code
  assert frame[4:6] == b"\x00\x01"  # register count = 1
  assert frame[6] == 0x02  # byte count = 2


# ========== V5 Frame ==========

def test_v5_build_frame_structure():
  """Verify start/end bytes, serial encoding, length field, and checksum."""
  modbus = build_modbus_read(1, 40, 1)
  frame = v5_build_frame(123456789, modbus)

  assert frame[0] == 0xA5
  assert frame[-1] == 0x15
  assert struct.unpack("<I", frame[7:11])[0] == 123456789
  assert struct.unpack("<H", frame[1:3])[0] == 15 + len(modbus)
  assert struct.unpack("<H", frame[3:5])[0] == 0x4510
  assert frame[-2] == sum(frame[1:-2]) & 0xFF


# ========== V5 Response Decoding ==========

def _build_v5_response(serial: int, modbus_frame: bytes) -> bytes:
  """Build a synthetic V5 response frame for testing."""
  payload_hdr = bytes([0x02]) + b"\x00" * 13  # 14-byte response payload header
  payload = payload_hdr + modbus_frame

  resp = bytearray()
  resp.append(0xA5)
  resp.extend(struct.pack("<H", len(payload)))
  resp.extend(struct.pack("<H", 0x1510))
  resp.extend(struct.pack("<H", 0x01))
  resp.extend(struct.pack("<I", serial))
  resp.extend(payload)
  resp.append(0x00)
  resp.append(0x15)
  resp[-2] = sum(resp[1:-2]) & 0xFF
  return bytes(resp)


def test_v5_decode_response_roundtrip():
  """Build a V5 response, decode it, verify we get the modbus frame back."""
  modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32]) + modbus_crc16(
      bytes([0x01, 0x03, 0x02, 0x00, 0x32])
  )
  decoded = v5_decode_response(_build_v5_response(123456789, modbus))
  assert decoded == modbus


def test_v5_decode_response_invalid_start():
  with pytest.raises(ValueError, match="Invalid V5 frame"):
    v5_decode_response(bytes([0x00] * 30))


def test_v5_decode_response_invalid_end():
  modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
  response = bytearray(_build_v5_response(123456789, modbus))
  response[-1] = 0x00  # break end byte (checked before checksum)
  with pytest.raises(ValueError, match="invalid end byte"):
    v5_decode_response(bytes(response))


def test_v5_decode_response_wrong_control_code():
  modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
  response = bytearray(_build_v5_response(123456789, modbus))
  response[3:5] = struct.pack("<H", 0x4510)  # change control code
  response[-2] = sum(response[1:-2]) & 0xFF  # recalculate checksum
  with pytest.raises(ValueError, match="V5 control code"):
    v5_decode_response(bytes(response))


def test_v5_decode_response_bad_checksum():
  modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
  response = bytearray(_build_v5_response(123456789, modbus))
  response[-2] = (response[-2] + 1) & 0xFF  # corrupt checksum
  with pytest.raises(ValueError, match="checksum mismatch"):
    v5_decode_response(bytes(response))


def test_v5_decode_response_wrong_frametype():
  modbus = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
  response = bytearray(_build_v5_response(123456789, modbus))
  response[11] = 0x01  # change frametype from 0x02 to 0x01
  response[-2] = sum(response[1:-2]) & 0xFF  # recalculate checksum
  with pytest.raises(ValueError, match="not a data frame"):
    v5_decode_response(bytes(response))


def test_v5_decode_response_modbus_too_short():
  short_modbus = bytes([0x01, 0x03])  # only 2 bytes, minimum is 5
  response = _build_v5_response(123456789, short_modbus)
  with pytest.raises(ValueError, match="Modbus frame too short"):
    v5_decode_response(response)


# ========== Modbus Response Parsing ==========

def test_parse_modbus_read_response():
  """Parse response with a single register value of 50."""
  frame = bytes([0x01, 0x03, 0x02, 0x00, 0x32, 0x39, 0x91])
  assert parse_modbus_read_response(frame) == [50]


def test_parse_modbus_error_response():
  """Error response (function code with high bit set) should raise ValueError."""
  frame = bytes([0x01, 0x83, 0x02])
  with pytest.raises(ValueError, match="Illegal Data Address"):
    parse_modbus_read_response(frame)
