# GPOE2025
repository for all things aurora: camera software, analysis scripts &amp; documentation

Feel free to commit everything to do with the project in the software realm!

## timelapse.py

This is an inital attempt at a customizable script for making timelapses with a Raspberry Pi HQ camera (Or Arducam brand, both with IMX477 sensors). To launch the script, call it from the command line as follows:

```
python3 timelapse.py -c timelapse_config.json
```

The `-c` (or `--config`) command line argument must be provided. The JSON file passed in contains all relevant parameters to define the timelapse. Currently the following parameters are implemented:

| Parameter Name | Description                |
| -------------- | -------------------------- |
| `num_frames`   | Numer of frames to capture |
| `capture_interval` | Time between frame captures |
| `run_id` | Name of the timelapse. Used for directory where image files are stored. If set to `"iso_date"`, uses the current ISO 8601-formatted date |
| `camera_controls` | A dictionary containing settings for the camera like exposure time and sensor gain. This dictionary is defined by the `Picamera2` library. |

The only dependencies for this script which aren't built-in Python libraries are `Picamera2` and `Numpy` both of which are installed by default on Raspberry Pi OS, so no package installation should be necessary.


## miscellany
- Don't install `h5py` like `pip install h5py`. This will throw an error like:
```
ImportError: libhdf5_serial.so.103: cannot open shared object file: No such file or directory
```
Instead, do:
`sudo apt-get install python3-h5py`

- check I2C devices:
      - run `i2cdetect -y 1`, you should see something like:
  
      ```
           0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
      00:                         -- -- -- -- -- -- -- -- 
      10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      20: -- 21 -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      50: 50 51 52 53 54 55 56 57 -- -- -- -- -- -- -- -- 
      60: -- -- -- -- -- -- -- -- UU -- -- -- -- -- -- -- 
      70: -- -- -- -- -- -- -- --    
      ```
  - `UU` indicates the clock is being used as a hardware clokc
  - `21` is the magnetometer (sometimes it's also `20`, `23`... we need to get this set to a fixed value
  - `50 - 57` might be the camera-- currently unknown
