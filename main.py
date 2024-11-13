import os
import sys
import asyncio
from datetime import datetime, timezone

import numpy as np

from data import _create_files
from data import insert_datum

from measure import (
    prepare_camera,
    take_single_exposure,
    prepare_magnetometer,
    get_magnetometer_measurement,
    prepare_thermometer,
    get_temperature
)

from logger import setup_logger

log = None

SECONDS_TO_MINUTES = 1 / 60
SECONDS_TO_HOURS = SECONDS_TO_MINUTES / 60
SECONDS_TO_DAYS = SECONDS_TO_HOURS / 24
SECONDS_TO_MICROSECONDS = 1_000_000

excess_minutes = 10
exposure_time = 15 # [seconds] 
exposure_cadence = 1 / 30 # [exposures per second]
exposure_timeout = 25 # [seconds]
measurement_cadence = 2 # [measurements per second]
measurement_timeout = 1 # [seconds]

# [seconds; the fastest an exposure + measurements can happen is > 15 seconds, so within a 30 second window we sleep for at most that time]
max_sleep = 15 

n_exposures = int(
    exposure_cadence / SECONDS_TO_HOURS
    + excess_minutes * exposure_cadence / SECONDS_TO_MINUTES
)
n_measurements = int(
    measurement_cadence / SECONDS_TO_HOURS
    + excess_minutes * measurement_cadence / SECONDS_TO_MINUTES
)

n_xpix = None
n_ypix = None
n_colors = None 

#parentdir = '/media/usb_drive'
parentdir = '/home/gpoe'

def get_now():
    """ Get's the current UTC time """
    now = datetime.now(timezone.utc)
    return now


def get_datestr(datetime):
    return datetime.isoformat().split('T')[0]


create_files = lambda outdir, name: _create_files(
    outdir, name, n_measurements, n_exposures, n_xpix, n_ypix
)


rm = None
cam = None
therm_device_file = None


async def get_measurements():
    e_mag, e_temp = None, None

    try:
        magnetic_field = get_magnetometer_measurement(rm)
    except Exception as e:
        magnetic_field = np.zeros((3,))
        e_mag = e

    try:
        temperature = get_temperature(therm_device_file)
    except Exception as e:
        temperature = 0
        e_temp = e    

    return (e_mag, e_temp), dict(
        temperature=temperature,
        magnetic_field=magnetic_field
    )


async def get_exposure():
    if cam is None:
        # if there's no camera, there's no wait for an exposure.
        # to make sure the timing doesn't get messed up, wait
        # that long anyway.
        await asyncio.sleep(exposure_time)

    image_arr = take_single_exposure(cam)
    return dict(
        exposure=image_arr
    )


async def main():
    start = get_now()
    start_of_day_timestamp = start.timestamp()
    start_of_hour_timestamp = start.timestamp()

    outdir = f'{parentdir}/{get_datestr(start)}'
    os.makedirs(outdir, exist_ok=True)

    exposure_file_path, measurement_file_path = create_files(
        outdir, start.hour
    )

    exposure_index = 0
    measurement_index = 0

    while True:
        current = get_now()
        current_timestamp = current.timestamp()

        target_end_timestamp = current_timestamp + 1 / exposure_cadence

        log.debug(f'current_timestamp= {current_timestamp}')

        if (current_timestamp - start_of_day_timestamp) * SECONDS_TO_DAYS > 1:
            start_of_day_timestamp = current_timestamp
            start_of_hour_timestamp = current_timestamp

            outdir = f'./{get_datestr(current)}'
    
            log.info(f'24 hours have passed; changing outdir to {outdir}')

            exposure_file_path, measurement_file_path = create_files(
                outdir, current.hour
            )

            exposure_index = 0
            measurement_index = 0

        elif (current_timestamp - start_of_hour_timestamp) * SECONDS_TO_HOURS > 1:
            start_of_hour_timestamp = current_timestamp

            log.info('1 hour has passed; making new measurement/exposure files')

            exposure_file_path, measurement_file_path = create_files(
                outdir, current.hour
            )

            exposure_index = 0
            measurement_index = 0

        exposure_start_timestamp = get_now().timestamp()
        exposure_task = asyncio.create_task(get_exposure())

        try:
            all_measurement_timestamps = []
            all_measurements = []
            all_measurement_indices = []
            
            # TODO: IM CLEARLY DOING SOMETHING WRONG BECAUSE THE MEASUREMENT TASK SEEMS TO WAIT FOR THE EXPOSURE TASK OR THE OTHER WAY AROUND
            # NEED TO MAKE A SIMPLE/CLEAN EXAMPLE
            while not exposure_task.done():
                measurement_timestamp = get_now().timestamp()
                try:
                    (e_mag, e_temp), measurements = await asyncio.wait_for(
                        get_measurements(),
                        timeout=measurement_timeout
                    )
                except asyncio.TimeoutError:
                    log.warning(f'timeout occured at {measurement_timestamp} when calling thermometer or magnetometer')
                    measurements = dict(
                        temperature=0,
                        magnetic_field=np.zeros(3)
                    )
    
                log.debug(
                    'measured temperature & magnetic field: '
                    f'temp = {measurements["temperature"]}, (Bx, By, Bz) = {measurements["magnetic_field"]}'
                )

                if e_mag is not None:
                    log.warning(f'error measuring magnetic field:\n{e_mag}')

                if e_temp is not None:
                    log.warning(f'error measuring temperature:\n{e_temp}')

                measurements = dict(
                    timestamp=measurement_timestamp,
                    **measurements
                )
                #insert_datum(
                #    measurement_file_path, measurements, measurement_index
                #)
                all_measurements.append(measurements)
                all_measurement_indices.append(measurement_index)
                all_measurement_timestamps.append(measurement_timestamp)
                measurement_index += 1
                #await asyncio.sleep(1 / measurement_cadence)
        except asyncio.CancelledError:
            log.info('Fast operations cancelled.')
        finally:
            try:
                exposure = await asyncio.wait_for(
                    exposure_task,
                    timeout=exposure_timeout
                )
            except asyncio.TimeoutError:
                log.warning(f'timeout occured at {exposure_start_timestamp} when calling camera')
                exposure = dict(exposure=np.zeros(n_xpix, n_ypix, n_colors, dtype=np.uint8))

            #log.info(f'gathered exposure')
                
            exposure_datum = dict(
                timestamp=exposure_start_timestamp,
                **exposure
            )
            insert_datum(
                exposure_file_path, exposure_datum, exposure_index
            )
            exposure_index += 1
        
        # once all of the above stuff is done, wait some delta # of seconds
        log.debug('exposure complete; running out the clock till the next exposure')
        sleep_length = min(
            target_end_timestamp - get_now().timestamp(),
            max_sleep
        )
        await asyncio.sleep(sleep_length)


if __name__ == '__main__':
    log = setup_logger('main-logger', sys.stdout, 'main', level='DEBUG')

    if not os.path.isdir(parentdir):
        log.warning(f'usb drive not found at {parentdir}. defaulting to /home/gpoe')
        parentdir = '/home/gpoe'

    try:
        cam = prepare_camera(exposure_time)
        log.info('setup camera')
    except Exception as e:
        log.warning(e)

    try:
        image_arr = take_single_exposure(cam)
        n_xpix, n_ypix, n_colors = image_arr.shape
        log.info('captured test exposure')
        log.debug(f'dims (n_xpix, n_ypix, n_colors) = {n_xpix, n_ypix, n_colors}')
    except Exception as e:
        log.warning(e)  
        n_xpix, n_ypix, n_colors = (1, 1, 3)

    try:
        rm = prepare_magnetometer()
        log.info('setup magnetometer')
    except Exception as e:
        log.warning(e) 
 
    try:
        therm_device_file = prepare_thermometer()
        log.info('setup thermometer')
    except Exception as e:
        log.warning(e)

    try:
        (e_mag, e_temp), meas = asyncio.run(get_measurements())
        log.info(
            'tested magnetometer & thermometer: '
            f'temp = {meas["temperature"]}, (Bx, By, Bz) = {meas["magnetic_field"]}'
        )

        if e_mag is not None:
            raise e_mag
        if e_temp is not None:
            raise e_temp
    except Exception as e:
        log.warning(e)

    asyncio.run(main())
