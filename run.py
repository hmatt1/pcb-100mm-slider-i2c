# go read https://github.com/hmatt1/adafruit-FT232H-my-demo to learn how to set this up!

import usb

print("usb:")
dev = usb.core.find(idVendor=0x0403, idProduct=0x6014)
print(dev)

from pyftdi.ftdi import Ftdi

# Just to display debugging info
#print("ftdi:")
#Ftdi().open_from_url('ftdi:///?')

def lower_ftdi_latency(i2c, ms=1):
    seen = set()
    stack = [i2c]
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if hasattr(obj, "set_latency_timer"):
            obj.set_latency_timer(ms)
            return True
        if hasattr(obj, "__dict__"):
            stack.extend(vars(obj).values())
    return False

import os
is_blinka_env_set = os.environ["BLINKA_FT232H"]
print(f"is_blinka_env_set: {is_blinka_env_set}")


import board
import time
import digitalio

import busio

print("--- Full Board Inspection ---")
print(f"board_id: {board.board_id}")
print(f"board_key: {board.board_key}")
print(f"board_module: {board.board_module}")
print(f"pin: {board.pin}")
print(dir(board))


led = digitalio.DigitalInOut(board.C0)
led.direction = digitalio.Direction.OUTPUT


i = 0
while i < 10:
    led.value = False
    time.sleep(0.1)
    led.value = True
    time.sleep(0.1)
    i = i + 1

# Backpack I2C Address (defined in Adafruit docs, and etched on the board)
ADDR = 0x70

print("i2c setup...")
i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)

while not i2c.try_lock():
    print("trying...")
    pass

if lower_ftdi_latency(i2c, 1):
    print("FTDI latency timer set to 1 ms")
else:
    print("could not reach the FTDI handle; still at 16 ms default")

addresses = i2c.scan()

for x in addresses:
    print(f"-> Device found at address: {hex(x)} (Decimal: {x})")
    if x == ADDR:
        print(f"   *** ADDR {hex(ADDR)} detected! ***")


# I2C slave address of the ADS112C04. This is set by the device's two
# address pins (both tied to GND in this wiring) and confirmed by the bus
# scan coming back with 0x40. It identifies the chip on the bus and is a
# separate thing from the command bytes below.
ADS_ADDR = 0x40

# All command bytes come from the command format in datasheet section 8.5.3.
# Each command is a single byte. Bits shown as x are don't-care, set to 0.

# RESET: format 0000 011x  ->  0000 0110
RESET = 0x06

# RREG, read a register: format 0010 rrxx
# rr is the 2-bit register number sitting in bits 3 and 2. xx are don't-care.
RREG0 = 0x20   # 0010 0000   rr = 00, register 0
RREG1 = 0x24   # 0010 0100   rr = 01, register 1
RREG2 = 0x28   # 0010 1000   rr = 10, register 2
RREG3 = 0x2C   # 0010 1100   rr = 11, register 3

# WREG, write a register: format 0100 rrxx, followed by the data byte.
# Same rr placement as RREG; only the top nibble changes from 0010 to 0100.
WREG0 = 0x40   # 0100 0000   rr = 00, register 0
WREG1 = 0x44   # 0100 0100   rr = 01, register 1
WREG2 = 0x48   # 0100 1000   rr = 10, register 2
WREG3 = 0x4C   # 0100 1100   rr = 11, register 3

def ads_read_reg(i2c, rreg_cmd):
    result = bytearray(1)
    i2c.writeto_then_readfrom(ADS_ADDR, bytes([rreg_cmd]), result)
    return result[0]

def ads_write_reg(i2c, wreg_cmd, value):
    i2c.writeto(ADS_ADDR, bytes([wreg_cmd, value]))

print("i2c resetting...")
i2c.writeto(ADS_ADDR, bytes([RESET]))
print("i2c after reset (expect 0x0):")
print(f"  reg0 -> {hex(ads_read_reg(i2c, RREG0))}")
print(f"  reg1 -> {hex(ads_read_reg(i2c, RREG1))}")
print(f"  reg2 -> {hex(ads_read_reg(i2c, RREG2))}")
print(f"  reg3 -> {hex(ads_read_reg(i2c, RREG3))}")

time.sleep(0.1)

print("i2c writing...")

ads_write_reg(i2c, WREG0, 0x01)
ads_write_reg(i2c, WREG1, 0x04)

print("i2c after writing config:")
print(f"  reg0 -> {hex(ads_read_reg(i2c, RREG0))}")
print(f"  reg1 -> {hex(ads_read_reg(i2c, RREG1))}")

time.sleep(0.1)

START = 0x08    # START/SYNC: 0000 1000, kicks off one conversion
RDATA = 0x10    # RDATA:      0001 0000, reads the latest conversion result

AVDD = 3.3      # set to your measured AVDD pin voltage

def ads_read_data(i2c):
    result = bytearray(2)
    i2c.writeto_then_readfrom(ADS_ADDR, bytes([RDATA]), result)
    return (result[0] << 8) | result[1]     # combine the two bytes into 16 bits

def ads_data_ready(i2c):
    return ads_read_reg(i2c, RREG2) & 0x80   # DRDY is bit 7 of register 2

def ads_read_voltage(i2c):
    i2c.writeto(ADS_ADDR, bytes([START]))    # start one conversion
    while not ads_data_ready(i2c):           # wait until the result is ready
        time.sleep(0.005)
    raw = ads_read_data(i2c)
    if raw & 0x8000:                          # 16-bit two's complement -> signed
        raw -= 0x10000
    return raw * AVDD / 32768                 # scale to volts against the reference

# AIN0 - AIN1, gain 1, PGA bypassed, AVDD as reference
ads_write_reg(i2c, WREG0, 0x01)
ads_write_reg(i2c, WREG1, 0x04)



import threading
import collections
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

GAIN = 1

# reg0: AIN0-AIN1, gain 1, PGA bypassed
# reg1: 0xDC = turbo, 2000 SPS, continuous conversion, AVDD reference
ads_write_reg(i2c, WREG0, 0x01)
ads_write_reg(i2c, WREG1, 0xDC)
i2c.writeto(ADS_ADDR, bytes([START]))      # start continuous conversions once

def ads_read_latest(i2c):
    raw = ads_read_data(i2c)               # RDATA only: no START, no DRDY poll
    if raw & 0x8000:
        raw -= 0x10000
    return raw * AVDD / GAIN / 32768


last_report = time.monotonic()
read_count = 0
rate = 0.0

data_lock = threading.Lock()
times = collections.deque(maxlen=8000)
volts = collections.deque(maxlen=8000)
start_time = time.monotonic()
running = True
count = 0

def acquire():
    global count
    while running:
        v = ads_read_latest(i2c)
        ts = time.monotonic() - start_time
        with data_lock:
            times.append(ts)
            volts.append(v)
            count += 1

worker = threading.Thread(target=acquire, daemon=True)
worker.start()

WINDOW_SECONDS = 5
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(10, 5))
fig.canvas.manager.set_window_title("ADS112C04 live")
(line,) = ax.plot([], [], color="#00e5ff", linewidth=1.5)
rate_text = ax.text(0.02, 0.95, "", transform=ax.transAxes,
                    fontsize=16, color="#00e5ff", va="top")
ax.set_xlabel("time (s)")
ax.set_ylabel("volts")
ax.set_ylim(0, 1.8)
ax.grid(True, alpha=0.2)
fig.tight_layout()

last_t = time.monotonic()
last_count = 0

def update(_):
    global last_t, last_count
    with data_lock:
        t = list(times)
        v = list(volts)
        c = count
    line.set_data(t, v)
    if t:
        ax.set_xlim(max(0, t[-1] - WINDOW_SECONDS), max(WINDOW_SECONDS, t[-1]))
    now = time.monotonic()
    dt = now - last_t
    sps = (c - last_count) / dt if dt > 0 else 0
    last_t, last_count = now, c
    rate_text.set_text(f"{v[-1]:.4f} V    {sps:.0f} samples/s" if v else "")
    return (line, rate_text)

ani = FuncAnimation(fig, update, interval=33, blit=False, cache_frame_data=False)

try:
    plt.show()
finally:
    running = False
    worker.join(timeout=1)
    i2c.unlock()
    i2c.deinit()
    print("shutting down...")