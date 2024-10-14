import os
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

SECONDS_TO_MINUTES = 1 / 60
SECONDS_TO_HOURS = SECONDS_TO_MINUTES / 60
SECONDS_TO_DAYS = SECONDS_TO_HOURS / 24
SECONDS_TO_MICROSECONDS = 1_000_000

excess_minutes = 10
exposure_time = 15 # [seconds] 
exposure_cadence = 1 / 30 # [exposures per second]
measurement_cadence = 1 # [measurements per second]

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
    magnetic_field = get_magnetometer_measurement(rm)
    temperature = get_temperature(therm_device_file)
    return dict(
        temperature=np.random.normal(loc=0, scale=1),
        magnetic_field=magnetic_field
    )


async def get_exposure():
    image_arr = take_single_exposure(cam)
    return dict(
        exposure=image_arr
    )


async def main():
    start = get_now()
    start_of_day_timestamp = start.timestamp()
    start_of_hour_timestamp = start.timestamp()

    outdir = f'./{get_datestr(start)}'
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

        print('current_timestamp=',current_timestamp)

        if (current_timestamp - start_of_day_timestamp) * SECONDS_TO_DAYS > 1:
            start_of_day_timestamp = current_timestamp
            start_of_hour_timestamp = current_timestamp

            outdir = f'./{get_datestr(current)}'
            exposure_file_path, measurement_file_path = create_files(
                outdir, current.hour
            )

            exposure_index = 0
            measurement_index = 0

        elif (current_timestamp - start_of_hour_timestamp) * SECONDS_TO_HOURS > 1:
            start_of_hour_timestamp = current_timestamp

            exposure_file_path, measurement_file_path = create_files(
                outdir, current.hour
            )

            exposure_index = 0
            measurement_index = 0

        # camera 
        # kick off an exposure...
        exposure_start_timestamp = get_now().timestamp()
        exposure_task = asyncio.create_task(get_exposure())

        try:
            while not exposure_task.done():
                measurement_timestamp = get_now().timestamp()
                measurements = await get_measurements()
                measurements = dict(
                    timestamp=measurement_timestamp,
                    **measurements
                )
                insert_datum(
                    measurement_file_path, measurements, measurement_index
                )
                measurement_index += 1
                await asyncio.sleep(1 / measurement_cadence)
        except asyncio.CancelledError:
            print("Fast operations cancelled.")
        finally:
            exposure = await exposure_task
            exposure_datum = dict(
                timestamp=exposure_start_timestamp,
                **exposure
            )
            insert_datum(
                exposure_file_path, exposure_datum, exposure_index
            )
            exposure_index += 1
        
        # once all of the above stuff is done, wait some delta # of seconds
        print('exposure complete; running out the clock...')
        await asyncio.sleep(
            (target_end_timestamp - get_now().timestamp()) #/ SECONDS_TO_MICROSECONDS
        )

        # this seems to run the CPU pretty hot!! was at ~100% utilization consistently
        #while get_now().timestamp() < target_end_timestamp:
        #    continue

        #print('all tasks done, measurement_index=',measurement_index,'exposure_index=',exposure_index)


if __name__ == '__main__':
    rm = prepare_magnetometer()
    cam = prepare_camera(exposure_time)
    therm_device_file = prepare_thermometer()

    print('Taking a test exposure... ', end='')
    image_arr = take_single_exposure(cam)
    print('done.')

    n_xpix, n_ypix, _ = image_arr.shape

    asyncio.run(main())
