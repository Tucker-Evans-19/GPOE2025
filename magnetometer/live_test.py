import time
import board
import rm3100

i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x20, cycle_count=400)

while True:
    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time) 
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading) 
        print(f'\r(Bx, By, Bz) = ({Bx:.3f}, {By:.3f}, {Bz:.3f}) µT', end='', flush=True)
        time.sleep(1)
    except OSError as e:
        print("OS ERROR", flush=True)
