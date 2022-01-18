import sys
import glob
import struct
from smbus2 import SMBus, i2c_msg

regs = {}


def find_goodix_gt911():
    devices = [int(dev[-2:]) for dev in glob.glob("/dev/i2c-*")]
    for dev in devices:
        for addr in (0x5d, 0x14):
            try:
                i2c_r = i2c_msg.read(addr, 4)
                i2c_w = i2c_msg.write(addr, (0x81, 0x40))
                SMBus(dev).i2c_rdwr(i2c_w, i2c_r)
                if list(i2c_r) == [57, 49, 49, 0]:  # 911\0
                    return addr, dev
            except OSError:
                pass
    return None, None


I2C_ADDRESS, I2C_BUS = find_goodix_gt911()


if I2C_BUS is None:
    print("Could not find GT911")
    sys.exit(1)

print(f"Found GT911 on /dev/i2c-{I2C_BUS}, address: 0x{I2C_ADDRESS:02x}")


bus = SMBus(I2C_BUS)


def calculate_checksum(regs):
    checksum = 0
    for reg, value in regs.items():
        checksum += value
    return (~checksum + 1) & 0xff


def read_reg(register):
    msg_w = i2c_msg.write(I2C_ADDRESS, struct.pack(">H", register))
    msg_r = i2c_msg.read(I2C_ADDRESS, 1)

    bus.i2c_rdwr(msg_w, msg_r)

    return list(msg_r)[0]


def write_reg(register, value):
    msg_w = i2c_msg.write(I2C_ADDRESS, struct.pack(">HB", register, value))
    msg_r = i2c_msg.read(I2C_ADDRESS, 1)

    bus.i2c_rdwr(msg_w)


fw_version = (read_reg(0x8145) << 8) | read_reg(0x8144)
print(f"Firmware version: 0x{fw_version:04x}")


for reg in range(0x8047, 0x80ff):
    regs[reg] = read_reg(reg)


# Read existing checksum
checksum = read_reg(0x80ff)

# Validate existing checksum
assert calculate_checksum(regs) == checksum

# Bit 7   = Reverse Y
# Bit 6   = Reverse X
# Bit 5,4 = Stretch Rank?
# Bit 3   = Swap X/Y
# Bit 2   = Software noise reduction
# Bit 1,0 = Interrupt trigger

# 0x35 = 00110101 = not working config
# 0x0d = 00001101 = works, but inverted on some?

TARGET_CONFIG = 0x0d | (1 << 7) | (0b11 << 4)

print(f"Attempting to set 0x804d to 0x{TARGET_CONFIG:02x}")

if regs[0x804d] == TARGET_CONFIG:
    print("Working config detected! Bailing.")
    sys.exit(0)

# Make changes
regs[0x804d] = TARGET_CONFIG 

# Calculate new checksum
checksum = calculate_checksum(regs)

# Write register values
for reg, value in regs.items():
    # print(f"0x{reg:04x}: 0x{value:02x} 0b{value:08b}")
    write_reg(reg, value)

# Write checksum
write_reg(0x80ff, checksum)

# Write update flag
write_reg(0x8100, 0x01)

# Verify
changed_regs = {}

for reg in range(0x8047, 0x80ff):
    changed_regs[reg] = read_reg(reg)

assert calculate_checksum(changed_regs) == checksum

print(f"All okay!")
