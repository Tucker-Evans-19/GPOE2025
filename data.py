import os
import sys
from copy import copy

import h5py
import numpy as np

from logger import setup_logger
log = setup_logger('data-logger', sys.stdout, 'data')


def _create_file(path, dataset_parameters, chunk_size=None):
    """
    path: must NOT have h5py on the end
    n_expected: int, the number of integers expected
    """
    
    orig_name, ext = os.path.splitext(path)

    i = 2
    while os.path.isfile(path):
        log.warning(f'file {path} already exists; incrementing version')
        path = f'{orig_name}-v{i}{ext}'
        i += 1

    log.debug(f'making file at {path}')

    if ext == '.hdf5':
        with h5py.File(path, 'w', rdcc_nbytes=1024**2*10) as f:
            for params in dataset_parameters:
                f.create_dataset(**params)
                log.debug(f'made dataset with parameters {params}')
    elif ext == '.txt':
        with open(path, 'w') as f:
            header = ''
            for params in dataset_parameters:
                col = params['name'].rjust(params['col_width'])
                header += col 
            np.savetxt(
                f, np.zeros(len(dataset_parameters))[None, :], header=header
            )
    else:
        raise ValueError(f'{ext} isnt a valid extension')

    return path


def _create_files(
    outdir, name, n_measurements, n_exposures, n_xpix, n_ypix, n_colors=3
):
    exposure_dataset_parameters = [
        dict(name='timestamp', shape=(n_exposures,), dtype=np.float64),
        dict(
            name='exposure',
            shape=(n_exposures, n_xpix, n_ypix, n_colors),
            dtype=np.uint8,
            chunks=(1, n_xpix, n_ypix, n_colors)
        )
    ]

    measurement_dataset_parameters = [
        dict(name='timestamp', col_width=18),
        dict(name='temperature', col_width=18),
        dict(name='bx', col_width=18),
        dict(name='by', col_width=18),
        dict(name='bz', col_width=18),
    ]

    exposure_file_path = _create_file(
        f'{outdir}/{name}-exposures.hdf5',
        exposure_dataset_parameters
    )

    log.info(f'made exposure file at {exposure_file_path}')

    measurement_file_path = _create_file(
        f'{outdir}/{name}-measurements.txt',
        measurement_dataset_parameters
    )

    log.info(f'made measurement file at {measurement_file_path}')

    return exposure_file_path, measurement_file_path


def insert_datum(path, datum, index):
    _, ext = os.path.splitext(path)

    if ext == '.hdf5':
        log.info(f'start to insert at {path}')
        with h5py.File(path, 'r+') as f:
            for key, value in datum.items():
                f[key][index] = value
        log.info(f'done inserting at {path}')
    elif ext == '.txt':
        if len(datum.shape) == 1:
            datum = datum[None, :]
        with open(path, 'a') as f:
            np.savetxt(f, datum)
    else:
        raise ValueError(
            f'file at {path} must have either hdf5 or txt extension'
        )

def read_file(path, subset, ftype='hdf5'):
    """ read data from a measurement/exposure file. not intended to be performant, just for plotting/inspection

    path: path to the .hdf5 file with the data
    subset: either 'exposure', 'temperature' or 'magnetic_field'
    """

    valid_subsets = ['exposure', 'temperature', 'magnetic_field']
    if subset not in valid_subsets:
        raise ValueError(f'subset must be one of {valid_subsets}')

    if ftype == 'hdf5':
        if path[-4:] != 'hdf5':
            raise ValueError(f'unrecognized extension on {path}; must be .hdf5')

        with h5py.File(path, 'r') as f:
            timestamp = f['timestamp'][:]
            mask = timestamp > 0

            timestamp = timestamp[mask]
            data = f[subset][mask]
    
        log.info(f'read in {path}')

    elif ftype == 'txt':
        raise NotImplementedError('havent implemented numpy txt read yet')
    else:
        raise ValueError('invalid file type for reading')

    return timestamp, data


def read_files(outdir, name, subset=None):
    """ read all of the hourly-measurement files found in an outdir. not intended to be performant, just for plotting/inspection.

    outdir: directory (probably named like YYYY-MM-DD) with all the data taken on that date
    name: either 'exposures' or 'measurements'
    subset: either 'temperature' or 'magnetic_field' if name == 'measurements'
    """

    # TODO: make workable for numpy txt files

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

    # sort by timestamp -- os.listdir doesn't guarantee it lists files temporally
    sortidxs = np.argsort(timestamp)
    timestamp = timestamp[sortidxs]
    data = data[sortidxs]

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


def plot_exposures(outdir):
    """ WARNING: this will make a plot for each exposure!
    this is example code """
    from datetime import datetime
    import matplotlib.pyplot as plt

    _, data = read_files(outdir, 'exposures')

    for i, d in enumerate(data):
        fig, ax = plt.subplots()
        ax.imshow(d)
        fig.savefig(f'{outdir}/exposure-{i}.png')

