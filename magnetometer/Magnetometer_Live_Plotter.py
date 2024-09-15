# Note: ensure python and, smbus, and matplotlib are installed on the pi.

import smbus
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# I2C address of the RM3100 - might need to be changed.
RM3100_ADDR = 0x23

# Initialize I2C (bus number depends on your Raspberry Pi version)
bus = smbus.SMBus(1)

def read_magnetometer():
    try:
        # Read X-axis data (24-bit)
        x_high = bus.read_byte_data(RM3100_ADDR, 0x24)
        x_mid = bus.read_byte_data(RM3100_ADDR, 0x25)
        x_low = bus.read_byte_data(RM3100_ADDR, 0x26)
        x = (x_high << 16) | (x_mid << 8) | x_low
        if x & (1 << 23):  # Check if the 24-bit value is negative
            x -= (1 << 24)

        # Read Y-axis data (24-bit)
        y_high = bus.read_byte_data(RM3100_ADDR, 0x27)
        y_mid = bus.read_byte_data(RM3100_ADDR, 0x28)
        y_low = bus.read_byte_data(RM3100_ADDR, 0x29)
        y = (y_high << 16) | (y_mid << 8) | y_low
        if y & (1 << 23):
            y -= (1 << 24)

        # Read Z-axis data (24-bit)
        z_high = bus.read_byte_data(RM3100_ADDR, 0x2A)
        z_mid = bus.read_byte_data(RM3100_ADDR, 0x2B)
        z_low = bus.read_byte_data(RM3100_ADDR, 0x2C)
        z = (z_high << 16) | (z_mid << 8) | z_low
        if z & (1 << 23):
            z -= (1 << 24)

        return x, y, z

    except IOError as e:
        print(f"Error reading magnetometer: {e}")
        return None, None, None

# Initialize lists to store data for plotting
x_data, y_data, z_data, time_data = [], [], [], []

# Set up the plot
fig, ax = plt.subplots()
ax.set_title("Live Magnetometer Data")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Magnetic Field Strength")

# Plot lines for X, Y, and Z axes
line_x, = ax.plot([], [], label='X-axis')
line_y, = ax.plot([], [], label='Y-axis')
line_z, = ax.plot([], [], label='Z-axis')

# Set plot limits
ax.set_xlim(0, 10)
ax.set_ylim(-1000, 1000)  # Adjust based on your magnetometer's range
plt.legend()

# Function to update the plot
def update(frame):
    x, y, z = read_magnetometer()
    if x is not None and y is not None and z is not None:
        # Update data
        time_data.append(time.time() - start_time)
        x_data.append(x)
        y_data.append(y)
        z_data.append(z)

        # Set to limit data to the last 10 seconds. (100 x 100ms = 10s) Feel free to update. Make sure the change plot x-axis too.
        if len(time_data) > 100:
            time_data.pop(0)
            x_data.pop(0)
            y_data.pop(0)
            z_data.pop(0)
        
        # Update plot lines
        line_x.set_data(time_data, x_data)
        line_y.set_data(time_data, y_data)
        line_z.set_data(time_data, z_data)
        
        # Rescale the x-axis based on the current time window
        ax.set_xlim(max(0, time.time() - start_time - 10), time.time() - start_time)

    return line_x, line_y, line_z

# Start time for the plot
start_time = time.time()

# Use FuncAnimation to update the plot in real-time
ani = FuncAnimation(fig, update, blit=True, interval=100)  # 100 ms refresh rate

# Show the plot
plt.show()
