import time
import board
import rm3100
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Initialize I2C and RM3100
i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x23)

# Initialize lists to store data for plotting
Bx_data, By_data, Bz_data, time_data = [], [], [], []

# Set up the plot
fig, ax = plt.subplots()
ax.set_title("Live Magnetometer Data")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Magnetic Field (µT)")

# Plot lines for Bx, By, and Bz
line_Bx, = ax.plot([], [], label='Bx')
line_By, = ax.plot([], [], label='By')
line_Bz, = ax.plot([], [], label='Bz')

# Set plot limits
ax.set_xlim(0, 10)  # Adjust depending on how much time you want to plot
ax.set_ylim(-100, 100)  # Adjust the range based on expected field strengths in µT
plt.legend()

# Start time for the plot
start_time = time.time()

# Function to update the plot
def update(frame):
    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time)
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading)

        # Update data
        time_data.append(time.time() - start_time)
        Bx_data.append(Bx)
        By_data.append(By)
        Bz_data.append(Bz)

        # Keep only the last 100 points (adjust for how much data you want to keep in the plot)
        if len(time_data) > 100:
            time_data.pop(0)
            Bx_data.pop(0)
            By_data.pop(0)
            Bz_data.pop(0)

        # Update plot lines
        line_Bx.set_data(time_data, Bx_data)
        line_By.set_data(time_data, By_data)
        line_Bz.set_data(time_data, Bz_data)

        # Rescale the x-axis based on the current time window
        ax.set_xlim(max(0, time.time() - start_time - 10), time.time() - start_time)

    except OSError as e:
        """Handle exception if needed"""
    
    return line_Bx, line_By, line_Bz

# Use FuncAnimation to update the plot in real-time
ani = FuncAnimation(fig, update, blit=True, interval=100)  # 100 ms refresh rate

# Show the plot
plt.show()

# Main loop to print values to the console (no change from your original script)
while True:
    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time)
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading)
        print(f'\r(Bx, By, Bz) = ({Bx:.3f}, {By:.3f}, {Bz:.3f}) µT', end='', flush=True)
    except OSError as e:
        """ """
