import os
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
            dtype=np.uint8
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


def read_file(path, subset):
    """ read data from a measurement/exposure file. not intended to be performant, just for plotting/inspection

    path: path to the .hdf5 file with the data
    subset: either 'exposure', 'temperature' or 'magnetic_field'
    """

    valid_subsets = ['exposure', 'temperature', 'magnetic_field']
    if subset not in valid_subsets:
        raise ValueError(f'subset must be one of {valid_subsets}')

    if path[-4:] != 'hdf5':
        raise ValueError(f'unrecognized extension on {path}; must be .hdf5')

    print(f'reading in {path}...', end='')
    with h5py.File(path, 'r') as f:
        timestamp = f['timestamp'][:]
        data = f[subset][:]
        return timestamp, data
    print('done.')


def read_files(outdir, name, subset=None):
    """ read all of the hourly-measurement files found in an outdir. not intended to be performant, just for plotting/inspection.

    outdir: directory (probably named like YYYY-MM-DD) with all the data taken on that date
    name: either 'exposures' or 'measurements'
    subset: either 'temperature' or 'magnetic_field' if name == 'measurements'
    """

    files = [
        f'{outdir}/{file}'
        for file in os.listdir(outdir)
        if file[-4:] == 'hdf5' and name in file
    ]

    subset = 'exposure' if name == 'exposures' else subset 

    timestamp, data = read_file(files[0], subset)
    for file in files[1:]:
        _t, _d = read_file(file, subset)
        timestamp = np.concatenate((timestamp, _t))
        data = np.concatenate((data, _d))

    return timestamp, data


def plot_files(outdir, name, subset=None):
    """ this is example code """
    from datetime import datetime
    import matplotlib.pyplot as plt

    timestamp, data = read_files(outdir, name, subset=subset)

    # convert integer timestamp into python datetime object
    # because matplotlib (should) handle these correctly
    timestamp = [
        datetime.utcfromtimestamp(t)
        for t in timestamp
    ]

    fig, ax = plt.subplots()
    ax.plot(timestamp, data)
    fig.savefig(f'{outdir}/{name}.png')

