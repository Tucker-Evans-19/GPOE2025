import os
import sys
import asyncio
from time import time, sleep
from datetime import datetime, timezone, timedelta

import numpy as np

from data import _create_files
from data import insert_datum
import json
import argparse
import schedule

parser = argparse.ArgumentParser()
parser.add_argument('--config', '-c', help='path to JSON config file', default='DEFAULT_CONFIG.json')
parser.add_argument(
    '--verbose',
    '-v',
    help='log debug statements to stdout',
    action='store_true'
)
parser.add_argument('--now', '-n', action='store_true', help='ignore the `observation_start_time` argument in config, and start taking observations immediately')
args = parser.parse_args()

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

with open(args.config, "rb") as file:
    config_dict = json.load(file)

excess_minutes = 10  # buffer the hdf5 file size by some amount
exposure_time = config_dict["exposure_duration"] # [seconds] 
exposure_cadence = 1 / config_dict["exposure_interval"] # [exposures per second]
exposure_timeout = 100 # [seconds]
measurement_cadence = config_dict["measurement_cadence"] # [seconds; approx]
camera_gain = config_dict["camera_gain"]

frames_per_night = (config_dict["observation_interval"]*3600)/config_dict["exposure_interval"] # osb interval is units of hrs

sleep_buffer = 1.0 

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

parentdir = '/media/usb_drive'

def get_now():
    """ Get's the current UTC time """
    now = datetime.now(timezone.utc)
    return now


def get_datestr(datetime):
    return datetime.isoformat().split('T')[0]


create_files = lambda outdir, name: _create_files(
    outdir, name, n_measurements, n_exposures, n_xpix, n_ypix, config=config_dict
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
        task = asyncio.create_task(insert_datum_async(path, datum, index))
        async with asyncio.timeout(60):
            await task #insert_datum_async(path, datum, index)
    except asyncio.TimeoutError:
        log.error(f'timeout when writing to {path} at index {index}')
    except asyncio.CancelledError:
        log.info('cancelled while inserting datum; finishing insert before')
        
        ntries = 0
        while not task.done() and ntries < 10:
            await asyncio.sleep(1)
            ntries += 1

        if task.done():
            raise
        else:
            log.warning('insert not yet finished, file may be corrupted!')

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

    return np.array([
        timestamp,
        temperature,
        *magnetic_field    
    ])


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

    count = 0

    exposure_file_path, measurement_file_path = create_files(
        outdir, count
    )

    exposure_index = 0
    measurement_index = 0

    # TODO: kick off the event loop at some determined/fixed/'round' time?
    for frame_num in range(0, int(frames_per_night)):
        current = get_now()
        current_timestamp = current.timestamp()
        target_end_timestamp = current_timestamp + 1 / exposure_cadence
        
        # TODO: move all of this into it's own function for clarity
        if (current_timestamp - start_of_day_timestamp) * SECONDS_TO_DAYS > 1:
            start_of_day_timestamp = current_timestamp
            start_of_hour_timestamp = current_timestamp

            outdir = f'./{get_datestr(current)}'
    
            log.info(f'24 hours have passed; changing outdir to {outdir}')

            count = 0

            exposure_file_path, measurement_file_path = create_files(
                outdir, count
            )

            exposure_index = 0
            measurement_index = 0

        elif (current_timestamp - start_of_hour_timestamp) * SECONDS_TO_HOURS > 1:
            start_of_hour_timestamp = current_timestamp

            log.info('1 hour has passed; making new measurement/exposure files')

            count += 1

            exposure_file_path, measurement_file_path = create_files(
                outdir, count
            )

            exposure_index = 0
            measurement_index = 0
 
        exposure_task = asyncio.create_task(get_and_write_exposure(
            exposure_file_path,
            exposure_index
        ))

        while target_end_timestamp - sleep_buffer > get_now().timestamp():
            measurement_index = await get_and_write_measurements(
                measurement_file_path,
                measurement_index
            )

        # since we dont wait `exposure_task` to finish, we go ahead and
        # increment to the next index
        exposure_index += 1

        approx_sleep_length = target_end_timestamp - get_now().timestamp()
        if approx_sleep_length < 0:
            log.warning(f'sleep length = {approx_sleep_length:.3e} < 0')
        else:
            log.info(f'sleeping ~{approx_sleep_length:.1f}s')
            sleep_length = target_end_timestamp - get_now().timestamp()
            await asyncio.sleep(sleep_length)


def time_until_observation():
    now = datetime.now()
    task_datetime = datetime.combine(now.date(), datetime.strptime(config_dict["observation_start_time"], "%H:%M").time())
    if task_datetime < now:  # If the time has passed today, set it for tomorrow
        task_datetime += timedelta(days=1)

    return (task_datetime - now).total_seconds()    

if __name__ == '__main__':
    level = 'DEBUG' if args.verbose else 'INFO'
    log = setup_logger('main-logger', sys.stdout, 'main', level=level)

    if not os.path.isdir(parentdir):
        # TODO: raise an error and crash if a 'usb_critical flag is set'
        log.warning(
            f'usb drive not found at {parentdir}. defaulting to /home/gpoe'
        )
        parentdir = '/home/gpoe'

    try:
        log.info("Sleeping for 1 min to wait to setup camera...")
        sleep(60)
        cam = prepare_camera(exposure_time, AnalogueGain=camera_gain)
        log.info('setup camera')
    except Exception as e:
        if camera_critical:
            log.error(e)
            raise e
        else:
            log.warning(e)

    try:
        # TODO: some kind of test to make sure we're actually getting
        # useful data? eg make sure there's at least some value > 0?        
        t1 = time()
        image_arr = take_single_exposure(cam)
        t2 = time()

        log.info(f'exposure & postprocessing took {t2 - t1:.3f} s')
        
        n_xpix, n_ypix, n_colors = image_arr.shape

        log.debug(
            f'dims (n_xpix, n_ypix, n_colors) = {n_xpix, n_ypix, n_colors}'
        )
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
    except Exception as e:
        log.warning(e)

    # Schedule the function
    #schedule.every().day.at(config_dict["observation_start_time"]).do(async_main)  # Example: 2:30 PM
    log.info(f"Observation scheduled to begin at: {config_dict['observation_start_time']}")

    begin_obs = False
    while True:
        time_to_start = time_until_observation()
        log.info(f"Time to observation start: {round(time_to_start, 2)} seconds")

        if not args.now:
            if time_to_start > 3600:
                log.info(f"Sleeping for 1 hour")
                sleep(3600)
            elif time_to_start > 600:
                log.info(f"Sleeping for 10 min")
                sleep(600)
            elif time_to_start > 60:
                log.info(f"Sleeping for 1 min")
                sleep(60)
            else:
                log.info(f"Sleeping until observation start time")
                sleep(time_to_start)
                begin_obs = True
        else:
            begin_obs = True

        if begin_obs:
            log.info(f"Beginning observations at {datetime.now().time()}")
            asyncio.run(main())
            begin_obs = False
