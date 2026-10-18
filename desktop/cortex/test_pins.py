"""
Pin test script: sequentially tests pins D2 to D13 to discover which pins control
the Red (Hours), Green (Minutes), and Blue (Seconds) LEDs on the BET RWU shield.
"""
import serial
import time

s = serial.Serial('COM4', 115200, timeout=1)
time.sleep(1.5)
print("Connected to Arduino on COM4")

# Set pin modes and toggle each pin for 0.5 seconds
for pin in range(2, 14):
    print(f"Testing Pin D{pin} HIGH...")
    s.write(f"SET {pin} 1\n".encode('ascii'))
    time.sleep(0.4)
    s.write(f"SET {pin} 0\n".encode('ascii'))
    time.sleep(0.1)

print("Scan complete.")
s.close()
