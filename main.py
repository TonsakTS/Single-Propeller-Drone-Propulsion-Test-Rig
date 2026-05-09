import network
import machine
import uasyncio as asyncio
import json
import time
from machine import Pin, PWM
from mpu6050 import MPU6050
from ina226 import INA226
from lidar import LidarSensor

# --- CONFIGURATION ---
WIFI_SSID = 'Horuas'
WIFI_PASSWORD = 'jjjjssss'

# --- HARDWARE SETUP (SENSORS) ---
# I2C_0 Bus: Shared by MPU6050 and Lidar
i2c_0 = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
mpu = MPU6050(i2c_0)
lidar = LidarSensor(i2c_0)

# I2C_1 Bus: Used exclusively by INA226
i2c_1 = machine.I2C(1, scl=machine.Pin(26), sda=machine.Pin(25), freq=400000)
ina = INA226(i2c_1)

# --- ESC / MOTOR SETUP ---
MOTOR_PIN = 18
motor = PWM(Pin(MOTOR_PIN), freq=50) 

DUTY_ARM = 40     # Guaranteed dead-zero to arm the ESC
DUTY_START = 55   # The exact duty cycle where your motor actually begins to spin
DUTY_MAX = 102    # Absolute maximum throttle

throttle_percent = 0
motor_armed = False

def update_esc():
    global throttle_percent
    # If stopped or at 0%, send the deep-zero arming signal
    if not motor_armed or throttle_percent == 0:
        motor.duty(DUTY_ARM)
        return
    
    # If armed and >0%, map 1-100% smoothly from DUTY_START to DUTY_MAX
    duty_range = DUTY_MAX - DUTY_START
    current_duty = int(DUTY_START + (throttle_percent / 100.0) * duty_range)
    motor.duty(current_duty)

# Arm ESC immediately on boot
motor.duty(DUTY_ARM)

# --- WEB PORTAL HTML (Login Removed) ---
HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>Drone Telemetry</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 20px; background-color: #f0f2f5; color: #000; }
        .header-title { font-size: 28px; font-weight: bold; margin-bottom: 20px; color: #333; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: inline-block; max-width: 500px; width: 100%; margin-bottom: 20px; }
        
        .data-section { border: 1px solid #e0e0e0; padding: 15px; margin-bottom: 15px; border-radius: 5px; text-align: left; background: #fafafa; }
        .data-section h3 { margin-top: 0; color: #0056b3; border-bottom: 2px solid #e0e0e0; padding-bottom: 5px; font-size: 18px; }
        .data-value { font-size: 15px; font-family: monospace; color: #000; margin: 5px 0; line-height: 1.5; }
        .error-text { color: #dc3545; font-weight: bold; }
        
        button { padding: 12px 20px; margin: 5px; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }
        .btn-green { background-color: #28a745; }
        .btn-red { background-color: #dc3545; }
        .btn-red:hover { background-color: #c82333; }
        .btn-orange { background-color: #fd7e14; }
        .btn-blue { background-color: #007bff; width: 40%; font-size: 20px; }
    </style>
</head>
<body>
    <div class="header-title">Drone Telemetry</div>

    <div id="dashboard">
        <div class="container">
            <h3>Motor Controls</h3>
            <p>Status: <span id="motor-status" style="font-weight:bold; color:#dc3545;">STOPPED</span></p>
            <p style="font-size: 24px;">Throttle: <span id="throttle-val" style="font-weight:bold;">0</span>%</p>
            
            <button class="btn-orange" onclick="motorCmd('start')">START</button>
            <button class="btn-red" onclick="motorCmd('stop')">E-STOP</button><br><br>
            <button class="btn-blue" onclick="motorCmd('down')">- 5%</button>
            <button class="btn-blue" onclick="motorCmd('up')">+ 5%</button>
        </div>

        <div class="container">
            <div class="data-section">
                <h3>Motion (MPU6050)</h3>
                <div id="motion-data" class="data-value">Waiting for data...</div>
            </div>
            
            <div class="data-section">
                <h3>Power (INA226)</h3>
                <div id="power-data" class="data-value">Waiting for data...</div>
            </div>
            
            <div class="data-section">
                <h3>Distance (VL53L0X)</h3>
                <div id="lidar-data" class="data-value">Waiting for data...</div>
            </div>
        </div>
    </div>

    <script>
        async function motorCmd(cmd) {
            let res = await fetch('/motor?cmd=' + cmd);
            if (res.ok) {
                let data = await res.json();
                document.getElementById('throttle-val').innerText = data.throttle;
                let statusEl = document.getElementById('motor-status');
                if(data.armed) {
                    statusEl.innerText = "ARMED & SPINNING";
                    statusEl.style.color = "#28a745";
                } else {
                    statusEl.innerText = "STOPPED";
                    statusEl.style.color = "#dc3545";
                }
            }
        }

        function formatSensorData(obj) {
            if (!obj) return "<span class='error-text'>No Data</span>";
            if (obj.error) {
                return `<span class="error-text">⚠ ${obj.error}</span>`;
            }
            let html = "";
            for (const [key, value] of Object.entries(obj)) {
                let displayVal = typeof value === 'object' ? JSON.stringify(value).replace(/\"/g, '') : value;
                html += `<strong>${key}:</strong> ${displayVal}<br>`;
            }
            return html;
        }

        async function fetchData() {
            try {
                let res = await fetch('/data');
                if (res.ok) {
                    let data = await res.json();
                    document.getElementById('motion-data').innerHTML = formatSensorData(data.motion);
                    document.getElementById('power-data').innerHTML = formatSensorData(data.power);
                    document.getElementById('lidar-data').innerHTML = formatSensorData(data.lidar);
                }
            } catch (e) {
                console.error("Fetch Error:", e);
            }
            
            // Auto-loop every 250ms
            setTimeout(fetchData, 250);
        }

        // Auto-start fetching data as soon as page loads
        window.onload = fetchData;
    </script>
</body>
</html>"""

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(0.5)
    
    try:
        if wlan.isconnected(): wlan.disconnect()
    except OSError:
        pass
        
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    time.sleep(1.0) 
    
    if not wlan.isconnected():
        print(f"Connecting to WiFi: {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
            
    ip = wlan.ifconfig()[0]
    print("\n=========================================")
    print("🚀 WiFi Connected Successfully!")
    print(f"👉 Click here to open dashboard: http://{ip}")
    print("=========================================\n")
    return ip

async def handle_api_request(reader, writer):
    try:
        request_line = await reader.readline()
        if not request_line: return
            
        while True:
            line = await reader.readline()
            if not line or line == b'\r\n': break

        req = request_line.decode('utf-8').split(' ')
        if len(req) < 2: return
            
        method = req[0]
        path = req[1]
        
        # --- HTML ROUTE ---
        if path == '/':
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n" + HTML_PAGE
            writer.write(response.encode('utf-8'))
            
        # --- MOTOR CONTROL ROUTE ---
        elif path.startswith('/motor'):
            global motor_armed, throttle_percent
            if "cmd=start" in path:
                motor_armed = True
                throttle_percent = 5
            elif "cmd=stop" in path:
                motor_armed = False
                throttle_percent = 0
            elif "cmd=up" in path:
                if motor_armed and throttle_percent < 100: throttle_percent = min(100, throttle_percent + 5)
            elif "cmd=down" in path:
                if motor_armed and throttle_percent > 0: throttle_percent = max(0, throttle_percent - 5)
            
            update_esc()
            status = json.dumps({"armed": motor_armed, "throttle": throttle_percent})
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + status
            writer.write(response.encode('utf-8'))

        # --- SENSOR DATA ROUTE ---
        elif path.startswith('/data'):
            combined_data = {
                "throttle_percent": throttle_percent,
                "motion": mpu.get_data(),
                "power": ina.get_data(),
                "lidar": lidar.get_data()
            }
            json_response = json.dumps(combined_data)
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n" + json_response
            writer.write(response.encode('utf-8'))
                
        else:
            writer.write("HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n".encode('utf-8'))
            
        await writer.drain()
        
    except Exception as e:
        print("Server Error:", e)
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    connect_wifi()
    server = await asyncio.start_server(handle_api_request, "0.0.0.0", 80)
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Script interrupted. Cutting motor power.")
    motor.duty(DUTY_ARM)