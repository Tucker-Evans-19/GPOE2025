import time
import board
import rm3100

i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x21)

while True:
    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time) 
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading) 
        print(f'\r(Bx, By, Bz) = ({Bx:.3f}, {By:.3f}, {Bz:.3f}) µT', end='', flush=True)
    except OSError as e:
        """ """
