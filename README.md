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
