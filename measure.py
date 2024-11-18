import os
import glob
import time

import numpy as np

from picamera2 import Picamera2

import board
import rm3100

SECONDS_TO_MICROSECONDS = 1_000_000


def prepare_camera(exposure_time, gain, **kwargs):
    """ exposure_time is in seconds """

    camera_controls = dict(
        ExposureTime=exposure_time * SECONDS_TO_MICROSECONDS,
        AnalogueGain=1,
        AeEnable=False
    )
    camera_controls.update(kwargs)

    cam = Picamera2()
    capture_config = cam.create_still_configuration(raw={}, display=None)
    capture_config["controls"] = camera_controls

    cam.configure(capture_config)
    cam.start()
    time.sleep(2) # TODO: is this nessecary? pulled it from timelapse.py
    
    return cam


def take_single_exposure(cam):
    if cam is None:
        image_arr = np.zeros((1, 1, 3), dtype=np.uint8)
    else:
        image_arr = cam.capture_array("main")
        image_arr = image_arr[:, 250:-480, :] # Cuts off all black regions of image and reduces data size by ~18 %
    return image_arr


def prepare_magnetometer():
    i2c = board.I2C()
    rm = rm3100.RM3100_I2C(i2c, i2c_address=0x20, cycle_count=400)
    return rm


def get_magnetometer_measurement(rm):
    if rm is None:
        Bx, By, Bz = (0, 0, 0)
    else:
        rm.start_single_reading()
        time.sleep(rm.measurement_time)
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading)
    return np.array([Bx, By, Bz])


def prepare_thermometer():
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')
 
    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'

    return device_file


def _read_temp(device_file):
    with open(device_file, 'r') as f:
        return f.readlines()


def get_temperature(device_file):
    if device_file is None:
        return 0

    lines = _read_temp(device_file)
    while lines[0].strip()[-3:] != 'YES':
        # time.sleep(0.2)
        lines = _read_temp()
    
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

