import time

class LidarSensor:
    def __init__(self, i2c, addr=0x29):
        self.i2c = i2c
        self.addr = addr
        self.is_ready = False
        self.tof = None
        self.error_msg = "Initializing..."
        self.init_sensor()

    def init_sensor(self):
        try:
            # Check if you uploaded the library file to the ESP32
            import vl53l0x
            
            # Ping the I2C bus to see if it is physically wired correctly
            self.i2c.readfrom(self.addr, 1)
            
            # Initialize the complex sensor sequence
            self.tof = vl53l0x.VL53L0X(self.i2c)
            self.tof.start()
            self.is_ready = True
        except ImportError:
            self.is_ready = False
            self.error_msg = "Missing 'vl53l0x.py' library file"
        except OSError:
            self.is_ready = False
            self.error_msg = "Lidar disconnected or wiring loose"

    def get_data(self):
        # Hot-swap and recovery check
        if not self.is_ready:
            self.init_sensor()
            if not self.is_ready:
                return {"error": self.error_msg}
                
        try:
            # Read actual distance in millimeters
            distance_mm = self.tof.read()
            
            # The sensor returns 8190 or 8191 when it is out of range
            if distance_mm > 8000:
                return {"status": "Out of Range (>2 meters)"}
                
            return {
                "distance_mm": distance_mm,
                "distance_cm": round(distance_mm / 10.0, 1)
            }
        except OSError:
            self.is_ready = False
            self.error_msg = "Lidar connection lost during read"
            return {"error": self.error_msg}