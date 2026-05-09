import machine
import struct

class MPU6050:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        self.is_ready = False
        self.wakeup()

    def wakeup(self):
        try:
            # Wake up the MPU6050
            self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')
            self.is_ready = True
        except OSError:
            self.is_ready = False

    def get_data(self):
        # If it wasn't there before, try to connect again (Hot-Swap)
        if not self.is_ready:
            self.wakeup()
            if not self.is_ready:
                return {"error": "MPU6050 missing or dead"}
                
        try:
            data = self.i2c.readfrom_mem(self.addr, 0x3B, 14)
            vals = struct.unpack('>hhhhhhh', data)
            
            ax = vals[0] / 16384.0
            ay = vals[1] / 16384.0
            az = vals[2] / 16384.0
            temp_c = (vals[3] / 340.0) + 36.53
            gx = vals[4] / 131.0
            gy = vals[5] / 131.0
            gz = vals[6] / 131.0
            
            return {
                "accel_g": {"x": round(ax, 3), "y": round(ay, 3), "z": round(az, 3)},
                "temp_C": round(temp_c, 2),
                "gyro_dps": {"x": round(gx, 2), "y": round(gy, 2), "z": round(gz, 2)}
            }
        except OSError:
            # If it gets unplugged while running, mark it as offline
            self.is_ready = False
            return {"error": "MPU6050 connection lost"}