import struct

class INA226:
    def __init__(self, i2c, addr=0x40):
        self.i2c = i2c
        self.addr = addr
        self.is_ready = False
        self.calibrate()

    def calibrate(self):
        try:
            # R010 (0.01 Ohm) Calibration -> 0x0200
            self.i2c.writeto_mem(self.addr, 0x05, b'\x02\x00')
            self.is_ready = True
        except OSError:
            self.is_ready = False

    def get_data(self):
        # If it wasn't there before, try to calibrate again (Hot-Swap)
        if not self.is_ready:
            self.calibrate()
            if not self.is_ready:
                return {"error": "INA226 missing or dead"}
                
        try:
            vbus_raw = self.i2c.readfrom_mem(self.addr, 0x02, 2)
            vbus_val = struct.unpack('>H', vbus_raw)[0]
            voltage_V = vbus_val * 0.00125  

            curr_raw = self.i2c.readfrom_mem(self.addr, 0x04, 2)
            curr_val = struct.unpack('>h', curr_raw)[0]
            current_mA = curr_val * 1.0  

            return {
                "voltage_V": round(voltage_V, 2),
                "current_mA": round(current_mA, 2),
                "power_mW": round(voltage_V * current_mA, 2)
            }
        except OSError:
             # If it gets unplugged while running, mark it as offline
            self.is_ready = False
            return {"error": "INA226 connection lost"}