from datetime import datetime
from measure import (
    prepare_magnetometer,
    prepare_thermometer,
    prepare_camera,
    get_temperature,
    get_magnetometer_measurement,
    take_single_exposure
)
import time

for _ in range(10):
    print('current datetime =', datetime.now())
    time.sleep(1)

try:
    rm = prepare_magnetometer()
    for _ in range(10):
        print('Bx, By, Bz =', get_magnetometer_measurement(rm))
        time.sleep(1)

except Exception as e:
    print('mag didnt work')
    print(e)

try:
    device_file = prepare_thermometer()
    for _ in range(10):
        print('temp =', get_temperature(device_file))
        time.sleep(1)
except Exception as e:
    print('tempt didnt work')
    print(e)

try:
    cam = prepare_camera(15)
    print('camera setup!')
    print('taking test exposure')
    image_arr = take_single_exposure(cam)
    print('done')
    print('dims =', image_arr.shape)
except Exception as e:
    print('camera didnt work')
    print(e)
