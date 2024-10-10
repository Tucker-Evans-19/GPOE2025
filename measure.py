import time

import numpy as np

import board
import rm3100


def prepare_magnetometer():
    i2c = board.I2C()
    rm = rm3100.RM3100_I2C(i2c, i2c_address=0x20, cycle_count=400)
    return rm


def get_magnetometer_measurement(rm):
    rm.start_single_reading()
    time.sleep(rm.measurement_time)
    reading = rm.get_next_reading()
    Bx, By, Bz =  rm.convert_to_microteslas(reading)
    return np.array([Bx, By, Bz])
