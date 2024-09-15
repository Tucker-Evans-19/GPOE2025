import h5py
import numpy as np


def _create_file(path, dataset_parameters):
    """
    path: must NOT have h5py on the end
    n_expected: int, the number of integers expected
    """
    
    # TODO: warnings in case the time fucks up and it drives to overwrite an
    # existing file... 

    # or maybe just have it append a 'v2' to the path

    f = h5py.File(path, 'w')

    for params in dataset_parameters:
        f.create_dataset(**params)

    return path


def _create_files(outdir, name, n_measurements, n_exposures, n_xpix, n_ypix, n_colors=3):
    exposure_dataset_parameters = [
        dict(name='timestamp', shape=(n_exposures,), dtype=np.float64),
        dict(
            name='exposure',
            shape=(n_exposures, n_xpix, n_ypix, n_colors),
            dtype=np.float64
        )
    ]

    measurement_dataset_parameters = [
        dict(name='timestamp', shape=(n_measurements,), dtype=np.float64),
        dict(name='temperature', shape=(n_measurements,), dtype=np.float32),
        dict(name='magnetic_field', shape=(n_measurements, 3), dtype=np.float32),
    ]

    exposure_file_path = _create_file(
        f'{outdir}/{name}-exposures.hdf5',
        exposure_dataset_parameters
    )

    measurement_file_path = _create_file(
        f'{outdir}/{name}-measurements.hdf5',
        measurement_dataset_parameters
    )

    return exposure_file_path, measurement_file_path


def insert_datum(path, datum, index):
    with h5py.File(path, 'r+') as f:
        for key, value in datum.items():
            f[key][index] = value


"""
example program loop:

path = create_file(...)

# measurements
for i in range(...):
    temperature = get_temperature(...)
    bx, by, bz = get_magnetic_filed(...)
    ...

"""

