import os
import asyncio
from datetime import datetime, timezone

import numpy as np

from data import _create_files
from data import insert_datum

SECONDS_TO_MINUTES = 1 / 60
SECONDS_TO_HOURS = SECONDS_TO_MINUTES / 60
SECONDS_TO_DAYS = SECONDS_TO_HOURS / 24

excess_minutes = 10
exposure_cadence = 1 / 15 # [exposures per second]
measurement_cadence = 1 # [measurements per second]

n_exposures = int(
    exposure_cadence / SECONDS_TO_HOURS
    + excess_minutes * exposure_cadence / SECONDS_TO_MINUTES
)
n_measurements = int(
    measurement_cadence / SECONDS_TO_HOURS
    + excess_minutes * measurement_cadence / SECONDS_TO_MINUTES
)

n_xpix = 100
n_ypix = 100


def get_now():
    """ Get's the current UTC time """
    now = datetime.now(timezone.utc)
    return now


def get_datestr(datetime):
    return datetime.isoformat().split('T')[0]


create_files = lambda outdir, name: _create_files(
    outdir, name, n_measurements, n_exposures, n_xpix, n_ypix
)


async def get_measurements():
    await asyncio.sleep(1)
    return dict(
        temperature=np.random.normal(loc=0, scale=1),
        magnetic_field=np.random.normal(loc=0, scale=1, size=(3,))
    )


async def get_exposure():
    await asyncio.sleep(30)
    return dict(
        exposure=np.random.normal(loc=0, scale=1, size=(n_xpix, n_ypix, 3)),
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
        except asyncio.CancelledError:
            print("Fast operations cancelled.")
        finally:
            exposure = await exposure_task
            exposure_datum = dict(
                timetamp=exposure_start_timestamp,
                exposure=exposure
            )
            insert_datum(
                exposure_file_path, exposure_datum, exposure_index
            )
            exposure_index += 1

        print('all tasks done, measurement_index=',measurement_index,'exposure_index=',exposure_index)


if __name__ == '__main__':
    asyncio.run(main())
