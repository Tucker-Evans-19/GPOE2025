import time
import board
import rm3100
from termcolor import colored

i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x21, cycle_count=400)

def get_color(meas):
    if meas > 40:
        return "red"
    elif meas > 20:
        return "yellow"
    else:
        return "green"

while True:
    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time) 
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading) 
        print(f'\r(Bx, By, Bz) = ({colored(Bx, get_color(Bx))}, {colored(By, get_color(By))}, {colored(Bz,get_color(Bz))}) µT')
        time.sleep(1)
    except OSError as e:
        print("OS ERROR", flush=True)
