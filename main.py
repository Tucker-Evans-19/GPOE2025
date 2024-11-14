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


camera_critical = False
thermometer_critical = True
magnetometer_critical = False


SECONDS_TO_MINUTES = 1 / 60
SECONDS_TO_HOURS = SECONDS_TO_MINUTES / 60
SECONDS_TO_DAYS = SECONDS_TO_HOURS / 24
SECONDS_TO_MICROSECONDS = 1_000_000

excess_minutes = 10
exposure_time = 15 # [seconds] 
exposure_cadence = 1 / 30 # [exposures per second]
exposure_timeout = 25 # [seconds]
#measurement_cadence = None # [measurements per second; determined by measurement time on magnetometer]
measurement_cadence = 1
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


async def insert_datum_async(path, datum, index):
    """ async wrapper around `insert_datum` """
    loop = asyncio.get_running_loop()    
    await loop.run_in_executor(None, insert_datum, path, datum, index)

async def insert_in_hdf5(path, datum, index):
    """ wraps `insert_datum_async` with error handling. Note, we take a fixed
        timeout for all writes of 2 seconds, as the largest items we'll write
        are the exposures which are ~6 MB, and write speed on the pi/usb
        seem to be of order >~ 10 MB/s    
    """
    try:
        await asyncio.wait_for(
            insert_datum_async(path, datum, index),
            timeout=2
        )
    except asyncio.TimeoutError:
        log.error(f'timeout when writing to {path} at index {index}')
    except Exception as e:
        log.error(e)


async def get_temperature_async():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        get_temperature,
        therm_device_file
    )


async def get_magnetometer_measurement_async():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        get_magnetometer_measurement,
        rm
    )


async def get_measurements():
    loop = asyncio.get_running_loop()

    timestamp = get_now().timestamp()

    try:
        temperature = await asyncio.wait_for(
            get_temperature_async(),
            timeout=1       
        )
    except asyncio.TimeoutError:
        temperature = 0
        log.error('thermometer timeout')
    except Exception as e:
        temperature = 0
        log.error(e)

    try:
        magnetic_field = await asyncio.wait_for(
            get_magnetometer_measurement_async(),
            timeout=5 * rm.measurement_time
        )
    except asyncio.TimeoutError:
        magnetic_field = np.zeros((3,))
        log.error('magnetometer timeout')
    except Exception as e:
        magnetic_field = np.zeros((3,))
        log.error(e) 

    log.debug(
        'measured temperature & magnetic field: '
        f'temp = {temperature}, '
        f'(Bx, By, Bz) = {magnetic_field}'
    )

    return dict(
        timestamp=timestamp,
        temperature=temperature,
        magnetic_field=magnetic_field
    )


async def get_and_write_measurements(path, index, event=None):
    """
    Take measurements & write them to an hdf5 file. Note that even if the
    measurement process or write fails, it will still increment the index;
    this allows us to compute statistics for failed measurements/writes later.

    path: str, path to hdf5 file to write
    index: int, index in the appropriate dataset(s) to write
    event: asyncio.Event, optional event to wait for
    """

    datum = await get_measurements()
    await insert_in_hdf5(path, datum, index)

    if event is not None:
        await event.wait()
 
    return index + 1 


async def take_single_exposure_async():
    """ async wrapper around `take_single_exposure` """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, take_single_exposure, cam)


async def get_exposure():
    timestamp = get_now().timestamp()

    if cam is None:
        # if there's no camera, there's no wait for an exposure.
        # to make sure the timing doesn't get messed up, wait
        # that long anyway.
        # I want to replace this with asyncio.Event synchronization at some
        # point b/c it's cleaner.
        await asyncio.sleep(exposure_time)

    try:
        image_arr = await asyncio.wait_for(
            take_single_exposure_async(),
            timeout=exposure_timeout
        )
    except asyncio.TimeoutError:
        log.error('exposure timeout')
        image_arr = np.zeros((n_xpix, n_ypix, n_colors), dtype=np.uint8)
    except Exception as e:
        log.error(e)
        image_arr = np.zeros((n_xpix, n_ypix, n_colors), dtype=np.uint8)

    return dict(
        timestamp=timestamp,
        exposure=image_arr
    )


async def get_and_write_exposure(path, index, event=None):
    datum = await get_exposure()
    await insert_in_hdf5(path, datum, index)
    
    if event is not None:
        await event.wait()

    return index + 1


async def main():
    loop = asyncio.get_event_loop()

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
        
        # TODO: move all of this into it's own function for clarity
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

        exposure_task = asyncio.create_task(get_and_write_exposure(
            exposure_file_path,
            exposure_index
        ))

        try:
            while not exposure_task.done():
                measurement_index = await get_and_write_measurements(
                    measurement_file_path,
                    measurement_index
                )
        except asyncio.CancelledError:
            log.info('Temperature/magnetic field measurements cancelled.')
        finally:
            await exposure_task
            exposure_index = exposure_task.result() 

        # once all of the above stuff is done, wait some delta # of seconds
        approx_sleep_length = target_end_timestamp - get_now().timestamp() 
        log.debug(
            f'exposure complete; waiting ~{approx_sleep_length:.1f}s '
            'until next exposure'
        )
        if approx_sleep_length < 0:
            log.warning(
                f'exposure + measurement loop took more than '
                f'{1 / exposure_cadence}s; '
                f'loop went over by {abs(approx_sleep_length):.3e}s'
            )
        elif approx_sleep_length > max_sleep:
            log.warning(
                f'exposure + measurement loop took less than {max_sleep}s'
            )

        # for the most exact sleep length, we want this to be the very last
        # operation of any kind in the loop
        sleep_length = min(
            target_end_timestamp - get_now().timestamp(),
            max_sleep
        )
        await asyncio.sleep(sleep_length)


if __name__ == '__main__':
    log = setup_logger('main-logger', sys.stdout, 'main', level='DEBUG')

    if not os.path.isdir(parentdir):
        # TODO: raise an error and crash if a 'usb_critical flag is set'
        log.warning(
            f'usb drive not found at {parentdir}. defaulting to /home/gpoe'
        )
        parentdir = '/home/gpoe'

    try:
        cam = prepare_camera(exposure_time)
        log.info('setup camera')
    except Exception as e:
        if camera_critical:
            log.error(e)
            raise e
        else:
            log.warning(e)

    try:
        #image_arr = asyncio.run(get_exposure())
        from time import time
        t1 = time()
        image_arr = take_single_exposure(cam)
        t2 = time()
        print(f'op took {t2 - t1} s')
        n_xpix, n_ypix, n_colors = image_arr.shape
        log.info('captured test exposure')
        log.debug(
            f'dims (n_xpix, n_ypix, n_colors) = {n_xpix, n_ypix, n_colors}'
        )
        log.debug(f'exposure looks like: {image_arr}')
        quit()
    except Exception as e:
        if camera_critical:
            log.error(e)
            raise e
        else:
            log.warning(e)  
        n_xpix, n_ypix, n_colors = (1, 1, 3)

    try:
        rm = prepare_magnetometer()
        log.info('setup magnetometer')
    except Exception as e:
        if magnetometer_critical:
            log.error(e)
            raise e
        else:
            log.warning(e) 
 
    try:
        therm_device_file = prepare_thermometer()
        log.info('setup thermometer')
    except Exception as e:
        if thermometer_critical:
            log.error(e)
            raise e
        else:
            log.warning(e)

    try:
        meas = asyncio.run(get_measurements())
        log.info(
            'tested magnetometer & thermometer: '
            f'temp = {meas["temperature"]}, '
            f'(Bx, By, Bz) = {meas["magnetic_field"]}'
        )
    except Exception as e:
        log.warning(e)

    asyncio.run(main())
