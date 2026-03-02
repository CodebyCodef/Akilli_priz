"""Quick verification script to run all tests without pytest color issues."""
import sys
import os
import struct
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol import encrypt, decrypt
from models import DeviceInfo, EnergyInfo

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        failed += 1

print("=== Protocol Tests ===")
# Roundtrip
msg = '{"system":{"get_sysinfo":{}}}'
check("roundtrip", decrypt(encrypt(msg)) == msg)

# Go vector - info
msg2 = '{"system":{"get_sysinfo":null}}'
expected = [208,242,129,248,139,255,154,247,213,239,148,182,209,180,192,159,236,149,230,143,225,135,232,202,240,158,235,135,235,150,235]
check("go_vector_info", list(encrypt(msg2)[4:]) == expected)

# Go vector - emeter
msg3 = '{"emeter":{"get_realtime":null}}'
expected3 = [208,242,151,250,159,235,142,252,222,228,159,189,218,191,203,148,230,131,226,142,250,147,254,155,185,131,237,152,244,152,229,152]
check("go_vector_emeter", list(encrypt(msg3)[4:]) == expected3)

# Go vector - on
msg4 = '{"system":{"set_relay_state":{"state":1}}}}'
expected4 = [208,242,129,248,139,255,154,247,213,239,148,182,197,160,212,139,249,156,240,145,232,183,196,176,209,165,192,226,216,163,129,242,134,231,147,246,212,238,223,162,223,162,223]
check("go_vector_on", list(encrypt(msg4)[4:]) == expected4)

# Length header
check("length_header", struct.unpack(">I", encrypt("hello")[:4])[0] == 5)

# Empty message
check("empty_message", len(encrypt("")) == 4)

print("\n=== Model Tests ===")
raw_info = {"alias": "Test", "relay_state": 1, "led_off": 0, "rssi": -40, "on_time": 100}
info = DeviceInfo.from_raw("1.2.3.4", raw_info)
check("device_info_on", info.is_on == True)
check("device_info_led", info.is_led_on == True)
check("device_info_alias", info.alias == "Test")

raw_off = {"relay_state": 0, "led_off": 1}
info_off = DeviceInfo.from_raw("1.2.3.4", raw_off)
check("device_info_off", info_off.is_on == False)
check("device_info_led_off", info_off.is_led_on == False)

eraw = {"voltage_mv": 220000, "current_ma": 500, "power_mw": 110000, "total_wh": 5000}
energy = EnergyInfo.from_raw(eraw)
check("energy_voltage", energy.voltage_v == 220.0)
check("energy_current", abs(energy.current_a - 0.5) < 0.001)
check("energy_power", energy.power_w == 110.0)

print("\n=== Device Client Tests ===")
from device import HS110Device

# Mock test
response = {"system": {"get_sysinfo": {"alias": "MockPlug", "model": "HS110", "mac": "AA:BB", "relay_state": 1, "led_off": 0, "rssi": -30, "on_time": 100}}}
mock_resp = encrypt(json.dumps(response, separators=(",", ":")))

with patch("device.socket.socket") as mock_cls:
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [mock_resp, b""]
    mock_cls.return_value = mock_sock
    dev = HS110Device("1.2.3.4")
    info2 = dev.get_sysinfo()
    check("mock_sysinfo_alias", info2.alias == "MockPlug")
    check("mock_sysinfo_is_on", info2.is_on == True)
    check("mock_sysinfo_model", info2.model == "HS110")

# Turn on command
resp_on = {"system": {"set_relay_state": {"err_code": 0}}}
mock_resp_on = encrypt(json.dumps(resp_on, separators=(",", ":")))
with patch("device.socket.socket") as mock_cls:
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [mock_resp_on, b""]
    mock_cls.return_value = mock_sock
    dev = HS110Device("1.2.3.4")
    dev.turn_on()
    sent_data = mock_sock.sendall.call_args[0][0]
    decrypted_cmd = json.loads(decrypt(sent_data))
    check("turn_on_command", decrypted_cmd == {"system": {"set_relay_state": {"state": 1}}})

# Repr
check("device_repr", repr(HS110Device("10.0.0.1")) == "HS110Device(ip='10.0.0.1', port=9999)")

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print("SOME TESTS FAILED!")
    sys.exit(1)
