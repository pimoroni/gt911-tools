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


read = i2c_msg.read(I2C_ADDRESS, 4)
bus.i2c_rdwr(i2c_msg.write(I2C_ADDRESS, (0x81, 0x40)), read)


def read_reg(register, length=1):
    msg_w = i2c_msg.write(I2C_ADDRESS, struct.pack(">H", register))
    msg_r = i2c_msg.read(I2C_ADDRESS, length)

    bus.i2c_rdwr(msg_w, msg_r)

    result = list(msg_r)[0] if length == 1 else list(msg_r)

    return result


product_id = [chr(x) for x in read_reg(0x8140, 4)]
product_id = "".join(product_id)
print(f"Product ID: {product_id}")


vendor_id = read_reg(0x814A)
print(f"Vendor ID: 0x{vendor_id:02x}")

fw_version = struct.unpack("<H", bytes(read_reg(0x8144, 2)))[0]
print(f"Firmware version: 0x{fw_version:04x}")

